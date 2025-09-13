from app.tools.base_interpreter import BaseCodeInterpreter
from app.tools.notebook_serializer import NotebookSerializer
import jupyter_client
from app.utils.log_util import logger
import os
import re
import asyncio
import shutil
from app.services.redis_manager import redis_manager
from app.schemas.response import (
    OutputItem,
    ResultModel,
    StdErrModel,
    SystemMessage,
)


class LocalCodeInterpreter(BaseCodeInterpreter):
    def __init__(
        self,
        task_id: str,
        work_dir: str,
        notebook_serializer: NotebookSerializer,
    ):
        super().__init__(task_id, work_dir, notebook_serializer)
        self.km, self.kc = None, None
        self.interrupt_signal = False
        # 防止同一缺失模块反复安装造成死循环
        self._auto_install_tried: set[str] = set()

    async def initialize(self):
        # 本地内核一般不需异步上传文件，直接切换目录即可
        # 初始化 Jupyter 内核管理器和客户端
        logger.info("初始化本地内核")
        self.km, self.kc = jupyter_client.manager.start_new_kernel(
            kernel_name="python3"
        )
        self._pre_execute_code()

    def _pre_execute_code(self):
        init_code = (
            f"import os\n"
            f"work_dir = r'{self.work_dir}'\n"
            f"os.makedirs(work_dir, exist_ok=True)\n"
            f"os.chdir(work_dir)\n"
            f"print('当前工作目录:', os.getcwd())\n"
            # Matplotlib 中文与负号支持；并尽量动态注册常见中文字体
            f"import matplotlib as mpl\n"
            f"import matplotlib.pyplot as plt\n"
            f"from matplotlib import font_manager as fm\n"
            # 动态注册常见字体文件（存在才添加）
            f"_font_files = [\n"
            f"    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',\n"
            f"    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',\n"
            f"    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',\n"
            f"    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',\n"
            f"    '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',\n"
            f"]\n"
            f"for _f in _font_files:\n"
            f"    try:\n"
            f"        if os.path.exists(_f):\n"
            f"            fm.fontManager.addfont(_f)\n"
            f"    except Exception as _e:\n"
            f"        pass\n"
            # 额外扫描工作目录下 fonts/ 目录中的自带字体
            f"_user_font_dir = os.path.join(work_dir, 'fonts')\n"
            f"if os.path.isdir(_user_font_dir):\n"
            f"    for _root, _dirs, _files in os.walk(_user_font_dir):\n"
            f"        for _fn in _files:\n"
            f"            if _fn.lower().endswith(('.ttf', '.ttc', '.otf')):\n"
            f"                _p = os.path.join(_root, _fn)\n"
            f"                try:\n"
            f"                    fm.fontManager.addfont(_p)\n"
            f"                except Exception:\n"
            f"                    pass\n"
            # 设定优先字体族（与上面注册的字体家族名对应）
            f"plt.rcParams['font.sans-serif'] = [\n"
            f"    'Noto Sans CJK SC', 'WenQuanYi Zen Hei', 'WenQuanYi Micro Hei',\n"
            f"    'SimHei', 'Microsoft YaHei', 'PingFang SC', 'Hiragino Sans GB',\n"
            f"    'Source Han Sans SC', 'DejaVu Sans', 'sans-serif'\n"
            f"]\n"
            f"plt.rcParams['font.family'] = 'sans-serif'\n"
            f"plt.rcParams['axes.unicode_minus'] = False\n"
        )
        self.execute_code_(init_code)

    async def execute_code(self, code: str) -> tuple[str, bool, str]:
        logger.info(f"执行代码: {code}")
        #  添加代码到notebook
        self.notebook_serializer.add_code_cell_to_notebook(code)

        text_to_gpt: list[str] = []
        content_to_display: list[OutputItem] | None = []
        error_occurred: bool = False
        error_message: str = ""

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="开始执行代码"),
        )
        # 执行 Python 代码
        logger.info("开始在本地执行代码...")
        execution = self.execute_code_(code)

        # 若检测到缺失模块或 pip 安装失败，尝试自动安装后重试一次
        missing_mod = self._extract_missing_module(execution)
        pip_failed_pkg = None if missing_mod else self._extract_pkg_from_calledprocesserror(execution)
        target_pkg = missing_mod or pip_failed_pkg
        if target_pkg and target_pkg not in self._auto_install_tried:
            self._auto_install_tried.add(target_pkg)
            pkg_name = self._map_import_to_package(target_pkg)
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content=f"检测到缺失依赖触发: {target_pkg}，尝试安装包: {pkg_name}"),
            )
            ok, install_log = await self._auto_install(pkg_name)
            if ok:
                logger.info(f"自动安装 {pkg_name} 成功，重试执行代码")
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content=f"已安装 {pkg_name}，正在重试执行代码"),
                )
                # 覆盖之前的执行结果，进入正常处理流程
                execution = self.execute_code_(code)
            else:
                logger.error(f"自动安装 {pkg_name} 失败: {install_log}")
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content=f"自动安装 {pkg_name} 失败\n{install_log}", type="error"),
                )
        logger.info("代码执行完成，开始处理结果...")

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="代码执行完成"),
        )

        for mark, out_str in execution:
            if mark in ("stdout", "execute_result_text", "display_text"):
                text_to_gpt.append(self._truncate_text(f"[{mark}]\n{out_str}"))
                #  添加text到notebook
                content_to_display.append(
                    ResultModel(type="result", format="text", msg=out_str)
                )
                self.notebook_serializer.add_code_cell_output_to_notebook(out_str)

            elif mark in (
                "execute_result_png",
                "execute_result_jpeg",
                "display_png",
                "display_jpeg",
            ):
                # TODO: 视觉模型解释图像
                text_to_gpt.append(f"[{mark} 图片已生成，内容为 base64，未展示]")

                #  添加image到notebook
                if "png" in mark:
                    self.notebook_serializer.add_image_to_notebook(out_str, "image/png")
                    content_to_display.append(
                        ResultModel(type="result", format="png", msg=out_str)
                    )
                else:
                    self.notebook_serializer.add_image_to_notebook(
                        out_str, "image/jpeg"
                    )
                    content_to_display.append(
                        ResultModel(type="result", format="jpeg", msg=out_str)
                    )

            elif mark == "error":
                error_occurred = True
                error_message = self.delete_color_control_char(out_str)
                error_message = self._truncate_text(error_message)
                logger.error(f"执行错误: {error_message}")
                text_to_gpt.append(error_message)
                #  添加error到notebook
                self.notebook_serializer.add_code_cell_error_to_notebook(out_str)
                content_to_display.append(StdErrModel(msg=out_str))

        logger.info(f"text_to_gpt: {text_to_gpt}")
        combined_text = "\n".join(text_to_gpt)

        await self._push_to_websocket(content_to_display)

        return (
            combined_text,
            error_occurred,
            error_message,
        )

    def _extract_missing_module(self, execution: list[tuple[str, str]]) -> str | None:
        """从执行结果中解析 ModuleNotFoundError 缺失模块名"""
        for mark, out_str in execution:
            if mark == "error":
                # 常见形式: ModuleNotFoundError: No module named 'networkx'
                m = re.search(r"ModuleNotFoundError: No module named ['\"]?([A-Za-z0-9_\.\-]+)['\"]?", out_str)
                if m:
                    return m.group(1)
        return None

    def _map_import_to_package(self, import_name: str) -> str:
        """将 import 名映射到 pip/uv 包名（常见别名修正）"""
        mapping = {
            "sklearn": "scikit-learn",
            "PIL": "Pillow",
            "yaml": "PyYAML",
            "bs4": "beautifulsoup4",
            "cv2": "opencv-python",
            "Crypto": "pycryptodome",
            "dateutil": "python-dateutil",
            "torchvision": "torchvision",
            "torch": "torch",
        }
        return mapping.get(import_name, import_name)

    def _extract_pkg_from_calledprocesserror(self, execution: list[tuple[str, str]]) -> str | None:
        """从 CalledProcessError 日志中解析出 pip install 的目标包名（最佳努力）。"""
        pat = re.compile(r"pip', 'install', '([^']+)'")
        for mark, out_str in execution:
            if mark == "error":
                m = pat.search(out_str)
                if m:
                    return m.group(1)
        return None

    async def _auto_install(self, pkg_name: str) -> tuple[bool, str]:
        """优先通过 uv 安装，失败则尝试在内核中使用 pip 安装"""
        # 尝试 uv 安装
        if shutil.which("uv"):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "uv", "pip", "install", pkg_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                out, err = await proc.communicate()
                if proc.returncode == 0:
                    return True, (out or b"").decode("utf-8", "ignore")
                else:
                    uv_log = ((out or b"") + (err or b"")).decode("utf-8", "ignore")
                    logger.warning(f"uv 安装失败，转内核 pip：{uv_log}")
            except Exception as e:
                logger.warning(f"调用 uv 失败：{e}")

        # 回退：在内核中执行 pip 安装，确保与内核环境一致
        install_code = (
            "import sys, subprocess\n"
            f"print('Installing {pkg_name} via pip in kernel...')\n"
            f"subprocess.check_call([sys.executable, '-m', 'pip', 'install', '{pkg_name}'])\n"
            f"print('Installed {pkg_name}')\n"
        )
        result = self.execute_code_(install_code)
        # 只要没有 error 标记即视为成功
        for mark, out_str in result:
            if mark == "error":
                return False, out_str
        log = "\n".join(f"{m}: {s}" for m, s in result)
        return True, log

    def execute_code_(self, code) -> list[tuple[str, str]]:
        msg_id = self.kc.execute(code)
        logger.info(f"执行代码: {code}")
        # Get the output of the code
        msg_list = []
        while True:
            try:
                iopub_msg = self.kc.get_iopub_msg(timeout=1)
                msg_list.append(iopub_msg)
                if (
                    iopub_msg["msg_type"] == "status"
                    and iopub_msg["content"].get("execution_state") == "idle"
                ):
                    break
            except:
                if self.interrupt_signal:
                    self.km.interrupt_kernel()
                    self.interrupt_signal = False
                continue

        all_output: list[tuple[str, str]] = []
        for iopub_msg in msg_list:
            if iopub_msg["msg_type"] == "stream":
                if iopub_msg["content"].get("name") == "stdout":
                    output = iopub_msg["content"]["text"]
                    all_output.append(("stdout", output))
            elif iopub_msg["msg_type"] == "execute_result":
                if "data" in iopub_msg["content"]:
                    if "text/plain" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["text/plain"]
                        all_output.append(("execute_result_text", output))
                    if "text/html" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["text/html"]
                        all_output.append(("execute_result_html", output))
                    if "image/png" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["image/png"]
                        all_output.append(("execute_result_png", output))
                    if "image/jpeg" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["image/jpeg"]
                        all_output.append(("execute_result_jpeg", output))
            elif iopub_msg["msg_type"] == "display_data":
                if "data" in iopub_msg["content"]:
                    if "text/plain" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["text/plain"]
                        all_output.append(("display_text", output))
                    if "text/html" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["text/html"]
                        all_output.append(("display_html", output))
                    if "image/png" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["image/png"]
                        all_output.append(("display_png", output))
                    if "image/jpeg" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["image/jpeg"]
                        all_output.append(("display_jpeg", output))
            elif iopub_msg["msg_type"] == "error":
                # TODO: 正确返回格式
                if "traceback" in iopub_msg["content"]:
                    output = "\n".join(iopub_msg["content"]["traceback"])
                    cleaned_output = self.delete_color_control_char(output)
                    all_output.append(("error", cleaned_output))
        return all_output

    async def get_created_images(self, section: str) -> list[str]:
        """获取新创建的图片列表"""
        current_images = set()
        files = os.listdir(self.work_dir)
        for file in files:
            if file.endswith((".png", ".jpg", ".jpeg")):
                current_images.add(file)

        # 计算新增的图片
        new_images = current_images - self.last_created_images

        # 更新last_created_images为当前的图片集合
        self.last_created_images = current_images

        logger.info(f"新创建的图片列表: {new_images}")
        return list(new_images)  # 最后转换为list返回

    async def cleanup(self):
        # 关闭内核
        self.kc.shutdown()
        logger.info("关闭内核")
        self.km.shutdown_kernel()

    def send_interrupt_signal(self):
        self.interrupt_signal = True

    def restart_jupyter_kernel(self):
        """Restart the Jupyter kernel and recreate the work directory."""
        self.kc.shutdown()
        self.km, self.kc = jupyter_client.manager.start_new_kernel(
            kernel_name="python3"
        )
        self.interrupt_signal = False
        self._create_work_dir()

    def _create_work_dir(self):
        """Ensure the working directory exists after a restart."""
        os.makedirs(self.work_dir, exist_ok=True)
