import os
import re
from e2b_code_interpreter import AsyncSandbox
from app.schemas.response import (
    CoderMessage,
    ErrorModel,
    OutputItem,
    ResultModel,
    StdErrModel,
    StdOutModel,
    SystemMessage,
)
from app.utils.enums import AgentType
from app.utils.redis_manager import redis_manager
from app.utils.notebook_serializer import NotebookSerializer
from app.utils.log_util import logger
import asyncio
from app.config.setting import settings
import json
import base64

from app.utils.common_utils import get_current_files


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
        timeout,
    ) -> "E2BCodeInterpreter":
        """创建并初始化 E2BCodeInterpreter 实例"""
        instance = cls(workd_dir, task_id, notebook_serializer)
        await instance.initialize(timeout=timeout)
        return instance

    async def initialize(self, timeout: int = 3000):
        """异步初始化沙箱环境"""
        try:
            self.sbx = await AsyncSandbox.create(
                api_key=settings.E2B_API_KEY, timeout=timeout
            )
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

            # 只上传数据集文件
            files = [
                f for f in os.listdir(self.work_dir) if f.endswith((".csv", ".xlsx"))
            ]
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
            # "plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS']\n"
            # "plt.rcParams['axes.unicode_minus'] = False\n"
            # "plt.rcParams['font.family'] = 'sans-serif'\n"
        )
        await self.execute_code(init_code)

    def _truncate_text(self, text: str, max_length: int = 5000) -> str:
        """截断文本，保留开头和结尾的重要信息"""
        if len(text) <= max_length:
            return text

        half_length = max_length // 2
        return text[:half_length] + "\n... (内容已截断) ...\n" + text[-half_length:]

    async def execute_code(self, code: str) -> tuple[str, bool, str]:
        """执行代码并返回结果"""

        if not self.sbx:
            raise RuntimeError("沙箱环境未初始化")

        logger.info(f"执行代码: {code}")
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
        logger.info("开始在沙箱中执行代码...")
        execution = await self.sbx.run_code(code)  # 返回 Execution 对象
        logger.info("代码执行完成，开始处理结果...")

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="代码执行完成"),
        )

        # 处理执行错误
        if execution.error:
            error_occurred = True
            error_message = f"Error: {execution.error.name}: {execution.error.value}\n{execution.error.traceback}"
            error_message = self._truncate_text(error_message)
            logger.error(f"执行错误: {error_message}")
            text_to_gpt.append(delete_color_control_char(error_message))
            content_to_display.append(
                ErrorModel(
                    name=execution.error.name,
                    value=execution.error.value,
                    traceback=execution.error.traceback,
                )
            )
        # 处理标准输出和标准错误

        if execution.logs:
            if execution.logs.stdout:
                stdout_str = "\n".join(execution.logs.stdout)
                stdout_str = self._truncate_text(stdout_str)
                logger.info(f"标准输出: {stdout_str}")
                text_to_gpt.append(stdout_str)
                content_to_display.append(
                    StdOutModel(msg="\n".join(execution.logs.stdout))
                )
                self.notebook_serializer.add_code_cell_output_to_notebook(stdout_str)

            if execution.logs.stderr:
                stderr_str = "\n".join(execution.logs.stderr)
                stderr_str = self._truncate_text(stderr_str)
                logger.warning(f"标准错误: {stderr_str}")
                text_to_gpt.append(stderr_str)
                content_to_display.append(
                    StdErrModel(msg="\n".join(execution.logs.stderr))
                )

            # 处理执行结果
        if execution.results:
            for result in execution.results:
                # 1. 文本格式
                if str(result):
                    content_to_display.append(
                        ResultModel(type="result", format="text", msg=str(result))
                    )
                # 2. HTML格式
                if result._repr_html_():
                    content_to_display.append(
                        ResultModel(
                            type="result", format="html", msg=result._repr_html_()
                        )
                    )
                # 3. Markdown格式
                if result._repr_markdown_():
                    content_to_display.append(
                        ResultModel(
                            type="result",
                            format="markdown",
                            msg=result._repr_markdown_(),
                        )
                    )
                # 4. PNG图片（base64字符串，前端可直接渲染）
                if result._repr_png_():
                    content_to_display.append(
                        ResultModel(
                            type="result", format="png", msg=result._repr_png_()
                        )
                    )
                # 5. JPEG图片
                if result._repr_jpeg_():
                    content_to_display.append(
                        ResultModel(
                            type="result", format="jpeg", msg=result._repr_jpeg_()
                        )
                    )
                # 6. SVG
                if result._repr_svg_():
                    content_to_display.append(
                        ResultModel(
                            type="result", format="svg", msg=result._repr_svg_()
                        )
                    )
                # 7. PDF
                if result._repr_pdf_():
                    content_to_display.append(
                        ResultModel(
                            type="result", format="pdf", msg=result._repr_pdf_()
                        )
                    )
                # 8. LaTeX
                if result._repr_latex_():
                    content_to_display.append(
                        ResultModel(
                            type="result", format="latex", msg=result._repr_latex_()
                        )
                    )
                # 9. JSON
                if result._repr_json_():
                    content_to_display.append(
                        ResultModel(
                            type="result",
                            format="json",
                            msg=json.dumps(result._repr_json_()),
                        )
                    )
                # 10. JavaScript
                if result._repr_javascript_():
                    content_to_display.append(
                        ResultModel(
                            type="result",
                            format="javascript",
                            msg=result._repr_javascript_(),
                        )
                    )
                    # 处理主要结果
                # if result.is_main_result and result.text:
                #     result_text = self._truncate_text(result.text)
                #     logger.info(f"主要结果: {result_text}")
                #     text_to_gpt.append(result_text)
                #     self.notebook_serializer.add_code_cell_output_to_notebook(
                #         result_text
                #     )

        # 限制返回的文本总长度

        for item in content_to_display:
            if isinstance(item, dict):
                if item.get("type") in ["stdout", "stderr", "error"]:
                    text_to_gpt.append(item.get("content") or item.get("value") or "")
            elif isinstance(item, ResultModel):
                if item.format in ["text", "html", "markdown", "json"]:
                    text_to_gpt.append(f"[{item.format}]\n{item.msg}")
                elif item.format in ["png", "jpeg", "svg", "pdf"]:
                    text_to_gpt.append(
                        f"[{item.format} 图片已生成，内容为 base64，未展示]"
                    )

        combined_text = "\n".join(text_to_gpt)

        # 在代码执行完成后，立即同步文件
        try:
            await self.download_all_files_from_sandbox()
            logger.info("文件同步完成")
        except Exception as e:
            logger.error(f"文件同步失败: {str(e)}")

        # 保存到分段内容
        ## TODO: Base64 等图像需要优化
        await self._push_to_websocket(content_to_display)

        return (
            combined_text,
            error_occurred,
            error_message,
        )

    async def _push_to_websocket(self, content_to_display: list[OutputItem] | None):
        logger.info("执行结果已推送到WebSocket")

        agent_msg = CoderMessage(
            agent_type=AgentType.CODER,
            code_results=content_to_display,
            files=get_current_files(self.work_dir, "all"),
        )
        logger.debug(f"发送消息: {agent_msg.model_dump_json()}")
        await redis_manager.publish_message(
            self.task_id,
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
                if await self.sbx.is_running():
                    try:
                        await self.download_all_files_from_sandbox()
                    except Exception as e:
                        logger.error(f"下载文件失败: {str(e)}")
                    finally:
                        await self.sbx.kill()
                        logger.info("成功关闭沙箱环境")
                else:
                    logger.warning("沙箱已经关闭，跳过清理步骤")
        except Exception as e:
            logger.error(f"清理沙箱环境失败: {str(e)}")
            # 这里可以选择不抛出异常，因为这是清理步骤

    async def download_all_files_from_sandbox(self) -> None:
        """从沙箱中下载所有文件并与本地同步"""
        try:
            # 获取沙箱中的文件列表
            sandbox_files = await self.sbx.files.list("/home/user")
            sandbox_files_dict = {f.name: f for f in sandbox_files}

            # 获取本地文件列表
            local_files = set()
            if os.path.exists(self.work_dir):
                local_files = set(os.listdir(self.work_dir))

            # 下载新文件或更新已修改的文件
            for file in sandbox_files:
                try:
                    local_path = os.path.join(self.work_dir, file.name)
                    should_download = True

                    # 检查文件是否需要更新
                    if file.name in local_files:
                        # 这里可以添加文件修改时间或内容哈希的比较
                        # 暂时简单处理，有同名文件就更新
                        pass

                    if should_download:
                        content = await self.sbx.files.read(file.path)

                        # 确保目标目录存在
                        os.makedirs(self.work_dir, exist_ok=True)

                        # 写入文件
                        with open(local_path, "wb") as f:
                            if isinstance(content, str):
                                if "," in content:  # 处理data URL格式
                                    content = content.split(",")[1]
                                    content = base64.b64decode(content)
                                else:
                                    content = content.encode("utf-8")
                            f.write(content)
                        logger.info(f"同步文件: {file.name}")

                except Exception as e:
                    logger.error(f"同步文件 {file.name} 失败: {str(e)}")
                    continue

            logger.info("文件同步完成")

        except Exception as e:
            logger.error(f"文件同步失败: {str(e)}")

    async def shutdown_sandbox(self):
        """关闭沙箱环境"""
        logger.info("关闭沙箱环境")
        await self.cleanup()

    async def get_current_all_files_from_sandbox(self) -> list:
        return await self.sbx.files.list("/home/user")

    def __del__(self):
        """析构函数，确保资源被正确清理"""
        try:
            if hasattr(self, "sbx") and self.sbx:
                asyncio.create_task(self.cleanup())
        except Exception as e:
            logger.error(f"析构函数中清理资源失败: {str(e)}")
