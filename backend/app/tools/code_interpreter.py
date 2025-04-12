import os
import re
from typing import Any
from e2b_code_interpreter import Sandbox
from app.schemas.response import CodeExecutionResult, AgentMessage
from app.utils.enums import AgentType
from app.utils.redis_manager import redis_async_client
from app.utils.notebook_serializer import NotebookSerializer
from app.utils.log_util import logger
import asyncio


def delete_color_control_char(string):
    ansi_escape = re.compile(r"(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]")
    return ansi_escape.sub("", string)


class E2BCodeInterpreter:
    def __init__(
        self, dirs: dict, task_id: str, notebook_serializer: NotebookSerializer
    ):
        self.dirs = dirs  # project / work_dir / task_id /
        self.sbx = Sandbox(timeout=60 * 20)
        self.task_id = task_id
        self.notebook_serializer = notebook_serializer
        # 保存coder_agent 在 jupyter 中执行的 output 结果内容
        self.section_output: dict[str, dict[str, list[str]]] = {}
        # {
        #     "eda": {
        #         "content":["xxxx",],
        #         "images":["aa.png"]
        #     },
        # }
        self.created_images: list[str] = []  # 当前求解创建的图片

        # 在初始化时调用异步初始化方法
        asyncio.create_task(self._initialize())

    async def _initialize(self):
        """异步初始化方法"""
        await self._pre_execute_code()
        await self._upload_all_files()

    async def _upload_all_files(self):
        for file in os.listdir(self.dirs["data"]):
            with open(os.path.join(self.dirs["data"], file), "rb") as f:
                await self.sbx.files.write(file, f)

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
        print("执行代码")
        self.notebook_serializer.add_code_cell_to_notebook(code)

        text_to_gpt: list[str] = []
        content_to_display: list[tuple[str, Any]] = []  # 发送给前端
        error_occurred: bool = False
        error_message: str = ""

        execution = self.sbx.run_code(code)
        # 处理错误
        if execution.error:
            error_occurred = True
            error_message = (
                execution.error.name
                + "\n"
                + execution.error.value
                + "\n"
                + execution.error.traceback
            )
            text_to_gpt.append(delete_color_control_char(error_message))
            content_to_display.append(("error", str(error_message)))

        # 处理标准输出
        if execution.logs.stdout:
            stdout_str = str(execution.logs.stdout)  # 确保转换为字符串
            text_to_gpt.append(stdout_str)
            content_to_display.append(("text", stdout_str))
            self.notebook_serializer.add_code_cell_output_to_notebook(stdout_str)

        # 处理执行结果
        for res in execution.results:
            # 处理文本结果
            if res.text:
                text_to_gpt.append(str(res.text))  # 确保转换为字符串
                content_to_display.append(("text", str(res.text)))
                self.notebook_serializer.add_code_cell_output_to_notebook(res.text)

            # 处理图片结果
            if res.png:
                text_to_gpt.append("[image]")
                content_to_display.append(("image/png", res.png))
                self.notebook_serializer.add_image_to_notebook(res.png, "image/png")

            elif res.jpeg:
                text_to_gpt.append("[image]")
                content_to_display.append(("image/jpeg", res.jpeg))
                self.notebook_serializer.add_image_to_notebook(res.jpeg, "image/jpeg")

        # 保存到分段内容
        for val in content_to_display:
            self.add_section(val[0])
            self.add_content(val[0], val[1])
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
        agent_msg = AgentMessage(
            agent_type=AgentType.CODER,
            code_result=code_execution_result,
        )
        print(f"发送消息: {agent_msg.model_dump_json()}")  # 调试输出
        await redis_async_client.publish(
            f"task:{self.task_id}:messages",
            agent_msg.model_dump_json(),
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

    def download_all_files_from_sandbox(self) -> dict:
        """下载沙盒中的所有文件"""
        logger.info("下载沙盒中的所有文件")
        for file in self.sbx.files.list("./"):
            with open(os.path.join(self.dirs["jupyter"], file.name), "wb") as f:
                f.write(file)

    def shotdown_sandbox(self):
        logger.info("关闭沙盒")
        self.download_all_files_from_sandbox()
        self.sbx.kill()
