# from .jupyter_backend import JupyterKernel
from e2b_code_interpreter import Sandbox
from app.schemas.response import CodeExecutionResult, AgentMessage
from app.utils.enums import AgentType
from app.main import redis_async_client
# class CodeInterpreter:
#     def __init__(
#         self, work_dir: str, notebook_serializer
#     ):  # project / work_dir / task_id / jupyter
#         self.jupyter_kernel = JupyterKernel(
#             work_dir=work_dir, notebook_serializer=notebook_serializer
#         )


class E2BCodeInterpreter:
    def __init__(self, work_dir: str, task_id: str):
        self.work_dir = work_dir  # project / work_dir / task_id /
        self.sbx = Sandbox()
        self.task_id = task_id
        self._pre_execute_code()

    def _pre_execute_code(self):
        init_code = (
            "import matplotlib.pyplot as plt\n"
            # 更完整的中文字体配置
            "plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']\n"
            "plt.rcParams['axes.unicode_minus'] = False\n"
            "plt.rcParams['font.family'] = 'sans-serif'\n"
            # 设置DPI以获得更清晰的显示
        )
        self.execute_code(init_code)

    def execute_code(self, code: str):
        text_to_gpt = []
        content_to_display = {}  # 发送给前端
        error_occurred = False
        error_message = ""

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
            text_to_gpt.append(error_message)
            content_to_display["error"] = error_message

        # 处理标准输出
        if execution.logs.stdout:
            text_to_gpt.append(str(execution.logs.stdout))  # 确保转换为字符串
            content_to_display["text"] = execution.logs.stdout

        # 处理执行结果
        for res in execution.results:
            # 处理文本结果
            if res.text:
                text_to_gpt.append(str(res.text))  # 确保转换为字符串
            # 处理图片结果
            if res.png:
                text_to_gpt.append("[image]")
                content_to_display["image/png"] = res.png
            elif res.jpeg:
                text_to_gpt.append("[image]")
                content_to_display["image/jpeg"] = res.jpeg

        self._push_to_websocket(content_to_display, error_message)
        return (
            "\n".join(text_to_gpt),
            content_to_display,
            error_occurred,
            error_message,
        )

    def _push_to_websocket(self, content_to_display, error_message):
        code_execution_result = CodeExecutionResult(
            content=content_to_display,
            error=error_message,
        )
        agent_msg = AgentMessage(
            agent_type=AgentType.CODER,
            code_result=code_execution_result,
        )
        print(f"发送消息: {agent_msg.model_dump_json()}")  # 调试输出
        redis_async_client.publish(
            f"task:{self.task_id}:messages",
            agent_msg.model_dump_json(),
        )
