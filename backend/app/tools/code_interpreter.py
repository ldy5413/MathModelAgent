import os
import re
from typing import Any
from e2b_code_interpreter import Sandbox, AsyncSandbox
from app.schemas.response import CodeExecutionResult, CoderMessage
from app.utils.enums import AgentType
from app.utils.redis_manager import redis_manager
from app.utils.notebook_serializer import NotebookSerializer
from app.utils.log_util import logger
import asyncio
from app.config.setting import settings
from e2b_code_interpreter.models import (
    Execution,
)


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

    @classmethod
    async def create(
        cls,
        workd_dir: str,
        task_id: str,
        notebook_serializer: NotebookSerializer,
    ) -> "E2BCodeInterpreter":
        """创建并初始化 E2BCodeInterpreter 实例"""
        instance = cls(workd_dir, task_id, notebook_serializer)
        await instance.initialize()
        return instance

    async def initialize(self):
        """异步初始化沙箱环境"""
        try:
            self.sbx = await AsyncSandbox.create(api_key=settings.E2B_API_KEY)
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
            "import matplotlib as mpl\n"
            # 更通用的中文字体配置
            "import platform\n"
            "if platform.system() == 'Darwin':  # macOS\n"
            "    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang HK', 'STHeiti Light', 'Heiti TC']\n"
            "elif platform.system() == 'Windows':  # Windows\n"
            "    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']\n"
            "else:  # Linux\n"
            "    plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Droid Sans Fallback', 'Arial Unicode MS']\n"
            "\n"
            "plt.rcParams['axes.unicode_minus'] = False\n"
            "plt.rcParams['font.family'] = 'sans-serif'\n"
            "mpl.rcParams['figure.dpi'] = 300\n"  # 提高DPI以获得更清晰的显示
        )
        await self.execute_code(init_code)

    def _truncate_text(self, text: str, max_length: int = 1000) -> str:
        """截断文本，保留开头和结尾的重要信息"""
        if len(text) <= max_length:
            return text

        half_length = max_length // 2
        return text[:half_length] + "\n... (内容已截断) ...\n" + text[-half_length:]

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
            logger.info("开始在沙箱中执行代码...")
            execution = await self.sbx.run_code(code)  # 返回 Execution 对象
            logger.info("代码执行完成，开始处理结果...")

            # 处理标准输出和标准错误
            if execution.logs:
                if execution.logs.stdout:
                    stdout_str = "\n".join(execution.logs.stdout)
                    stdout_str = self._truncate_text(stdout_str)
                    logger.info(f"标准输出: {stdout_str}")
                    text_to_gpt.append(stdout_str)
                    content_to_display.append(("text", stdout_str))
                    self.notebook_serializer.add_code_cell_output_to_notebook(
                        stdout_str
                    )

                if execution.logs.stderr:
                    stderr_str = "\n".join(execution.logs.stderr)
                    stderr_str = self._truncate_text(stderr_str)
                    logger.warning(f"标准错误: {stderr_str}")
                    text_to_gpt.append(stderr_str)
                    content_to_display.append(("error", stderr_str))

            # 处理执行结果
            if execution.results:
                for result in execution.results:
                    # 处理主要结果
                    if result.is_main_result and result.text:
                        result_text = self._truncate_text(result.text)
                        logger.info(f"主要结果: {result_text}")
                        text_to_gpt.append(result_text)
                        content_to_display.append(("text", result_text))
                        self.notebook_serializer.add_code_cell_output_to_notebook(
                            result_text
                        )

                    # 处理图表结果
                    if result.chart:
                        logger.info("发现图表结果")
                        chart_data = result.chart.to_dict()
                        chart_str = str(chart_data)
                        if len(chart_str) > 1000:  # 限制图表数据大小
                            chart_str = "图表数据过大，已省略"
                        text_to_gpt.append(chart_str)
                        content_to_display.append(("chart", chart_data))

            # 处理执行错误
            if execution.error:
                error_occurred = True
                error_message = f"{execution.error.name}: {execution.error.value}\n{execution.error.traceback}"
                error_message = self._truncate_text(error_message)
                logger.error(f"执行错误: {error_message}")
                text_to_gpt.append(delete_color_control_char(error_message))
                content_to_display.append(("error", error_message))

            # 保存到分段内容
            for val in content_to_display:
                self.add_section(val[0])
                self.add_content(val[0], val[1])

            await self._push_to_websocket(content_to_display, error_message)
            logger.info("执行结果已推送到WebSocket")

        except Exception as e:
            logger.error(f"代码执行过程中发生异常: {str(e)}")
            error_occurred = True
            error_message = str(e)
            text_to_gpt.append(error_message)
            content_to_display.append(("error", error_message))
            await self._push_to_websocket(content_to_display, error_message)

        # 限制返回的文本总长度
        combined_text = "\n".join(text_to_gpt)
        if len(combined_text) > 5000:  # 设置一个合理的总长度限制
            combined_text = self._truncate_text(combined_text, 5000)

        return (
            combined_text,
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

    async def get_created_images(self, section: str) -> list[str]:
        """获取当前 section 创建的图片列表"""
        if not self.sbx:
            return []

        try:
            files = await self.sbx.files.list("./")
            for file in files:
                if file.path.endswith(".png") or file.path.endswith(".jpg"):
                    self.add_section(section)
                    self.section_output[section]["images"].append(file.name)

            self.created_images = list(
                set(self.section_output[section]["images"]) - set(self.created_images)
            )
            return self.created_images
        except Exception as e:
            logger.error(f"获取创建的图片列表失败: {str(e)}")
            return []

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
        try:
            if hasattr(self, "sbx") and self.sbx:
                asyncio.create_task(self.cleanup())
        except Exception as e:
            logger.error(f"析构函数中清理资源失败: {str(e)}")
