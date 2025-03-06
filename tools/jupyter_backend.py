import jupyter_client
import re
import os
from utils.logger import log
from utils.notebook_serializer import NotebookSerializer


def delete_color_control_char(string):
    ansi_escape = re.compile(r"(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]")
    return ansi_escape.sub("", string)


class JupyterKernel:
    def __init__(self, work_dir, notebook_serializer):
        self.work_dir = work_dir
        self.notebook_serializer = notebook_serializer

        self.kernel_manager, self.kernel_client = (
            jupyter_client.manager.start_new_kernel(kernel_name="python3")
        )
        self.interrupt_signal = False
        self._create_work_dir()
        self.available_functions = {
            "execute_code": self.execute_code,
            "python": self.execute_code,
        }

    def execute_code_(self, code) -> list[tuple[str, str]]:
        msg_id = self.kernel_client.execute(code)
        log.info(f"执行代码: {code}")
        # Get the output of the code
        msg_list = []
        while True:
            try:
                iopub_msg = self.kernel_client.get_iopub_msg(timeout=1)
                msg_list.append(iopub_msg)
                if (
                    iopub_msg["msg_type"] == "status"
                    and iopub_msg["content"].get("execution_state") == "idle"
                ):
                    break
            except:
                if self.interrupt_signal:
                    self.kernel_manager.interrupt_kernel()
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
                if "traceback" in iopub_msg["content"]:
                    output = "\n".join(iopub_msg["content"]["traceback"])
                    all_output.append(("error", output))
        return all_output

    def execute_code(self, code: str) -> tuple[str, list[tuple[str, str]], bool, str]:
        #  添加代码到notebook
        self.notebook_serializer.add_code_cell_to_notebook(code)

        text_to_gpt: list[str] = []
        content_to_display: list[tuple[str, str]] = self.execute_code_(code)
        error_occurred: bool = False
        error_message: str = ""

        for mark, out_str in content_to_display:
            if mark in ("stdout", "execute_result_text", "display_text"):
                text_to_gpt.append(out_str)
                #  添加text到notebook

                self.notebook_serializer.add_code_cell_output_to_notebook(out_str)

            elif mark in (
                "execute_result_png",
                "execute_result_jpeg",
                "display_png",
                "display_jpeg",
            ):
                # TODO: 视觉模型解释图像
                text_to_gpt.append("[image]")
                #  添加image到notebook
                if "png" in mark:
                    self.notebook_serializer.add_image_to_notebook(out_str, "image/png")
                else:
                    self.notebook_serializer.add_image_to_notebook(
                        out_str, "image/jpeg"
                    )

            elif mark == "error":
                error_occurred = True
                error_message = delete_color_control_char(out_str)
                text_to_gpt.append(error_message)
                #  添加error到notebook
                self.notebook_serializer.add_code_cell_error_to_notebook(out_str)
        log.debug("\ncontent_to_display:\n" + str(content_to_display))
        log.debug("\n\n执行代码:\n" + "\n".join(text_to_gpt))

        return "\n".join(text_to_gpt), content_to_display, error_occurred, error_message

    def _create_work_dir(self):
        self.work_dir = os.path.normpath(self.work_dir)

        init_code = (
            f"import os\n"
            f"work_dir = r'{self.work_dir}'\n"
            f"os.makedirs(work_dir, exist_ok=True)\n"
            f"os.chdir(work_dir)\n"
            f"print('当前工作目录:', os.getcwd())\n"
            f"import matplotlib.pyplot as plt\n"
# 更完整的中文字体配置
            f"plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']\n"
            f"plt.rcParams['axes.unicode_minus'] = False\n"
f"plt.rcParams['font.family'] = 'sans-serif'\n"
            # 设置DPI以获得更清晰的显示
        )
        self.execute_code_(init_code)

    def send_interrupt_signal(self):
        self.interrupt_signal = True

    def restart_jupyter_kernel(self):
        self.kernel_client.shutdown()
        self.kernel_manager, self.kernel_client = (
            jupyter_client.manager.start_new_kernel(kernel_name="python3")
        )
        self.interrupt_signal = False
        self._create_work_dir()

    def __del__(self):
        self.kernel_manager.shutdown_kernel()

    def close(self):
        if hasattr(self, "jupyter_kernel"):
            self.jupyter_kernel.shutdown()
