import os
import re
from typing import Any
from e2b_code_interpreter import Sandbox
from app.schemas.response import CodeExecutionResult, CoderMessage
from app.utils.enums import AgentType
from app.utils.redis_manager import redis_manager
from app.utils.notebook_serializer import NotebookSerializer
from app.utils.log_util import logger
import asyncio
from app.config.setting import settings


def delete_color_control_char(string):
    ansi_escape = re.compile(r"(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]")
    return ansi_escape.sub("", string)


class E2BCodeInterpreter:
    def __init__(
        self,
        workd_dir: str,
        task_id: str,
        notebook_serializer: NotebookSerializer,
    ):
        self.work_dir = workd_dir
        self.sbx = None
        self.task_id = task_id
        self.notebook_serializer = notebook_serializer
        self.section_output: dict[str, dict[str, list[str]]] = {}
        self.created_images: list[str] = []

        # 在初始化时调用异步初始化方法
        asyncio.create_task(self._initialize())

    async def _initialize(self):
        """异步初始化沙箱环境"""
        try:
            self.sbx = await Sandbox.create(api_key=settings.E2B_API_KEY)
            logger.info("沙箱环境初始化成功")
            await self._pre_execute_code()
            await self._upload_all_files()
        except Exception as e:
            logger.error(f"初始化沙箱环境失败: {str(e)}")
            raise

    async def _upload_all_files(self):
        """上传工作目录中的所有文件到沙箱"""
        try:
            logger.info(f"开始上传文件，工作目录: {self.work_dir}")
            if not os.path.exists(self.work_dir):
                logger.error(f"工作目录不存在: {self.work_dir}")
                raise FileNotFoundError(f"工作目录不存在: {self.work_dir}")

            files = os.listdir(self.work_dir)
            logger.info(f"工作目录中的文件列表: {files}")

            for file in files:
                file_path = os.path.join(self.work_dir, file)
                logger.info(f"处理文件: {file_path}")

                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "rb") as f:
                            content = f.read()
                            # 使用 files API 上传文件
                            await self.sbx.files.write(f"/home/user/{file}", content)
                            logger.info(f"成功上传文件到沙箱: {file}")
                    except Exception as e:
                        logger.error(f"上传文件 {file} 失败: {str(e)}")
                        raise
                else:
                    logger.info(f"跳过目录: {file_path}")

            # 验证上传的文件
            uploaded_files = await self.sbx.files.list("/home/user")
            logger.info(f"沙箱中的文件列表: {[f.name for f in uploaded_files]}")

        except Exception as e:
            logger.error(f"文件上传过程失败: {str(e)}")
            raise

    async def _pre_execute_code(self):
        init_code = (
            "import matplotlib.pyplot as plt\n"
            # 更完整的中文字体配置
            "plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']\n"
            "plt.rcParams['axes.unicode_minus'] = False\n"
            "plt.rcParams['font.family'] = 'sans-serif'\n"
            # 设置DPI以获得更清晰的显示
        )
        await self.execute_code(init_code)

    async def execute_code(self, code: str) -> tuple[str, list[str, Any], bool, str]:
        """执行代码并返回结果"""
        if not self.sbx:
            raise RuntimeError("沙箱环境未初始化")

        logger.info(f"执行代码: {code}")
        self.notebook_serializer.add_code_cell_to_notebook(code)

        text_to_gpt: list[str] = []
        content_to_display: list[tuple[str, Any]] = []
        error_occurred: bool = False
        error_message: str = ""

        try:
            # 执行 Python 代码
            result = await self.sbx.run_python(code)

            # 处理错误
            if result.error:
                error_occurred = True
                error_message = str(result.error)
                text_to_gpt.append(delete_color_control_char(error_message))
                content_to_display.append(("error", str(error_message)))

            # 处理标准输出
            if result.stdout:
                stdout_str = str(result.stdout)
                text_to_gpt.append(stdout_str)
                content_to_display.append(("text", stdout_str))
                self.notebook_serializer.add_code_cell_output_to_notebook(stdout_str)

            # 处理执行结果
            if result.output:
                text_to_gpt.append(str(result.output))
                content_to_display.append(("text", str(result.output)))
                self.notebook_serializer.add_code_cell_output_to_notebook(result.output)

            # 保存到分段内容
            for val in content_to_display:
                self.add_section(val[0])
                self.add_content(val[0], val[1])

            await self._push_to_websocket(content_to_display, error_message)

        except Exception as e:
            logger.error(f"代码执行失败: {str(e)}")
            error_occurred = True
            error_message = str(e)
            text_to_gpt.append(error_message)
            content_to_display.append(("error", error_message))
            await self._push_to_websocket(content_to_display, error_message)

        return (
            "\n".join(text_to_gpt),
            content_to_display,
            error_occurred,
            error_message,
        )

    async def _push_to_websocket(self, content_to_display, error_message):
        code_execution_result = CodeExecutionResult(
            content=content_to_display,
            error=error_message,
        )
        agent_msg = CoderMessage(
            agent_type=AgentType.CODER,
            code_result=code_execution_result,
        )
        logger.debug(f"发送消息: {agent_msg.model_dump_json()}")
        await redis_manager.publish_message(
            f"task:{self.task_id}:messages",
            agent_msg,
        )

    def get_created_images(self, section: str) -> list[str]:
        """获取当前 section 创建的图片列表"""
        for file in self.sbx.files.list("./"):
            if file.name.endswith(".png") or file.name.endswith(".jpg"):
                self.section_output[section]["images"].append(file.name)

        self.created_images = list(
            set(self.section_output[section]["images"]) - set(self.created_images)
        )
        return self.created_images

    def add_section(self, section_name: str) -> None:
        """确保添加的section结构正确"""

        if section_name not in self.section_output:
            self.section_output[section_name] = {"content": [], "images": []}

    def add_content(self, section: str, text: str) -> None:
        """向指定section添加文本内容"""
        self.add_section(section)
        self.section_output[section]["content"].append(text)

    def get_code_output(self, section: str) -> str:
        """获取指定section的代码输出"""
        return "\n".join(self.section_output[section]["content"])

    async def cleanup(self):
        """清理资源并关闭沙箱"""
        try:
            if self.sbx:
                await self.download_all_files_from_sandbox()
                await self.sbx.close()
                logger.info("成功关闭沙箱环境")
        except Exception as e:
            logger.error(f"清理沙箱环境失败: {str(e)}")
            raise

    async def download_all_files_from_sandbox(self) -> None:
        """从沙箱中下载所有文件"""
        try:
            files = await self.sbx.files.list("/home/user")
            for file in files:
                if file.is_file():
                    content = await self.sbx.files.read(file.path)
                    output_path = os.path.join(self.work_dir, file.name)
                    with open(output_path, "wb") as f:
                        f.write(content)
                    logger.info(f"成功下载文件: {file.name}")
        except Exception as e:
            logger.error(f"下载文件失败: {str(e)}")
            raise

    async def shutdown_sandbox(self):
        """关闭沙箱环境"""
        logger.info("关闭沙箱环境")
        await self.cleanup()

    def __del__(self):
        """析构函数，确保资源被正确清理"""
        if self.sbx:
            asyncio.create_task(self.cleanup())
