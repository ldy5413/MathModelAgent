import json
from core.LLM import BaseModel
from models.user_output import UserOutput
from tools.code_interpreter import CodeInterpreter
from utils.common_utils import get_current_files
from utils.enums import CompTemplate, FormatOutPut
from utils.logger import log
from utils.RichPrinter import RichPrinter
from utils.notebook_serializer import NotebookSerializer
from .functions import functions
from .prompt import *

class Agent:
    def __init__(
        self,
        model: BaseModel,
        max_chat_turns: int = 30,  # 单个agent最大对话轮次
        user_output: UserOutput = None,
    ) -> None:
        self.model = model
        self.chat_history: list[dict] = []  # 存储对话历史
        self.max_chat_turns = max_chat_turns  # 最大对话轮次
        self.current_chat_turns = 0  # 当前对话轮次计数器
        self.user_output = user_output

    def run(self, prompt: str, system_prompt: str) -> str:
        """
        执行agent的对话并返回结果和总结

        Args:
            prompt: 输入的提示

        Returns:
            str: 模型的响应
        """
        try:
            RichPrinter.agent_start(self.__class__.__name__)
            self.current_chat_turns = 0  # 重置对话轮次计数器

            # 更新对话历史
            self.append_chat_history({"role": "system", "content": system_prompt})
            self.append_chat_history({"role": "user", "content": prompt})

            # 获取历史消息用于本次对话
            response = self.model.chat(
                history=self.chat_history, agent_name=self.__class__.__name__
            )
            response_content = response.choices[0].message.content
            self.chat_history.append({"role": "assistant", "content": response_content})

            RichPrinter.agent_end(self.__class__.__name__)
            return response_content
        except Exception as e:
            error_msg = f"执行过程中遇到错误: {str(e)}"
            log.error(f"Agent执行失败: {str(e)}")
            return error_msg

    def append_chat_history(self, msg: dict) -> None:
        self.chat_history.append(msg)
        self.user_output.data_recorder.append_chat_history(
            msg, agent_name=self.__class__.__name__
        )


class ModelerAgent(Agent):  # 继承自Agent类而不是BaseModel
    def __init__(
        self,
        model: BaseModel,
        max_chat_turns: int = 30,  # 添加最大对话轮次限制
    ) -> None:
        super().__init__(model, max_chat_turns)
        self.system_prompt =MODELER_PROMPT

# 代码强
class CoderAgent(Agent):  # 同样继承自Agent类
    def __init__(
        self,
        model: BaseModel,
        work_dir: str,  # 工作目录
        max_chat_turns: int = 60,  # TODO: 配置文件
        max_retries: int = 5,  # 重试次数
        user_output: UserOutput = None,
    ) -> None:
        super().__init__(model, max_chat_turns, user_output)
        self.work_dir = work_dir
        self.notebook_serializer = NotebookSerializer(work_dir)
        self.code_interpreter = CodeInterpreter(work_dir, self.notebook_serializer)

        self.max_retries = max_retries
        self.is_first_run = True
        self.created_images: list[str] = []  # 当前任务创建的图片列表
        self.system_prompt = CODER_PROMPT

        self.created_images: list[str] = []  # 当前求解创建的图片

    def run(self, prompt: str, subtask_title: str) -> str:
        RichPrinter.agent_start(self.__class__.__name__)
        self.created_images.clear()  # 清空上一次任务的图片列表
        # TODO: jupyter 的notebook 分节
        self.notebook_serializer.add_markdown_segmentation_to_notebook(
            content=prompt, segmentation=subtask_title
        )

        # 如果是第一次运行，则添加系统提示
        if self.is_first_run:
            self.is_first_run = False
            self.append_chat_history({"role": "system", "content": self.system_prompt})

        self.append_chat_history({"role": "user", "content": prompt})

        retry_count = 0
        last_error_message = ""
        task_completed = False

        if self.current_chat_turns >= self.max_chat_turns:
            raise Exception(
                f"Reached maximum number of chat turns ({self.max_chat_turns}). Task incomplete."
            )

        if retry_count >= self.max_retries:
            raise Exception(
                f"Failed to complete task after {self.max_retries} attempts. Last error: {last_error_message}"
            )

        try:
            while (
                not task_completed
                and retry_count < self.max_retries
                and self.current_chat_turns < self.max_chat_turns
            ):
                self.current_chat_turns += 1
                response = self.model.chat(
                    history=self.chat_history,
                    tools=functions,
                    tool_choice="auto",
                    agent_name=self.__class__.__name__,
                )

                if (
                    hasattr(response.choices[0].message, "tool_calls")
                    and response.choices[0].message.tool_calls
                ):
                    tool_call = response.choices[0].message.tool_calls[0]
                    tool_id = tool_call.id
                    # TODO: json JSON解析时遇到了无效的转义字符
                    if tool_call.function.name == "execute_code":
                        code = json.loads(tool_call.function.arguments)["code"]
                        full_content = response.choices[0].message.content

                        # 更新对话历史 - 添加助手的响应
                        self.append_chat_history(
                            {
                                "role": "assistant",
                                "content": full_content,
                                "tool_calls": [
                                    {
                                        "id": tool_id,
                                        "type": "function",
                                        "function": {
                                            "name": "execute_code",
                                            "arguments": json.dumps({"code": code}),
                                        },
                                    }
                                ],
                            }
                        )

                        # 执行代码并获取结果
                        (
                            text_to_gpt,
                            content_to_display,
                            error_occurred,
                            error_message,
                        ) = self.code_interpreter.jupyter_kernel.execute_code(code)

                        # 添加工具执行结果
                        self.append_chat_history(
                            {
                                "role": "tool",
                                "content": text_to_gpt,
                                "tool_call_id": tool_id,
                            }
                        )

                        if error_occurred:
                            retry_count += 1
                            last_error_message = error_message
                            reflection_prompt = get_reflection_prompt(error_message,code)

                            self.append_chat_history(
                                {"role": "user", "content": reflection_prompt}
                            )
                            continue

                        # 检查任务完成情况时也计入对话轮次
                        self.current_chat_turns += 1
                        completion_check_prompt = get_completion_check_prompt(prompt, text_to_gpt)
                        self.append_chat_history(
                            {"role": "user", "content": completion_check_prompt}
                        )

                        completion_response = self.model.chat(
                            history=self.chat_history,
                            tools=functions,
                            tool_choice="auto",
                            agent_name=self.__class__.__name__,
                        )

                        # # TODO: 压缩对话历史
                        # if completion_response.usage.prompt_tokens > self.max_tokens * 0.75:
                        #     # 保留系统消息
                        #     system_messages = [msg for msg in self.chat_history if msg["role"] == "system"]
                        #     recent_messages = self.chat_history[-5:]
                        #     self.chat_history = system_messages + recent_messages
                        # elif completion_response.usage.prompt_tokens > self.max_tokens:
                        #     raise Exception("token超出限制")

                        if not (
                            hasattr(
                                completion_response.choices[0].message, "tool_calls"
                            )
                            and completion_response.choices[0].message.tool_calls
                        ):
                            task_completed = True
                            RichPrinter.agent_end(self.__class__.__name__)
                            return completion_response.choices[0].message.content
                if retry_count >= self.max_retries:
                    return f"Failed to complete task after {self.max_retries} attempts. Last error: {last_error_message}"

                if self.current_chat_turns >= self.max_chat_turns:
                    return f"Reached maximum number of chat turns ({self.max_chat_turns}). Task incomplete."

            RichPrinter.agent_end(self.__class__.__name__)
            self._update_created_images()
            return response.choices[0].message.content
        except Exception as e:
            error_msg = f"执行过程中遇到错误: {str(e)}"
            log.error(f"Agent执行失败: {str(e)}")
            return error_msg

    def get_created_images(self) -> list[str]:
        """获取当前任务创建的图片列表"""
        return self.created_images

    def _update_created_images(self) -> None:
        """更新创建的图片列表"""
        current_images = set(get_current_files(self.work_dir, "image"))
        previous_images = set(self.created_images)
        self.created_images = list(current_images - previous_images)

    def get_notebook_serializer(self) -> NotebookSerializer:
        return self.notebook_serializer


# 长文本
# TODO: 并行 parallel
class WriterAgent(Agent):  # 同样继承自Agent类
    def __init__(
        self,
        model: BaseModel,
        max_chat_turns: int = 10,  # 添加最大对话轮次限制
        comp_template: CompTemplate = CompTemplate,
        format_output: FormatOutPut = FormatOutPut.Markdown,
        user_output: UserOutput = None,
    ) -> None:
        super().__init__(model, max_chat_turns, user_output)
        self.format_out_put = format_output
        self.comp_template = comp_template
        self.system_prompt = get_writer_prompt(format_output)
        self.available_images: list[str] = []

    def run(self, prompt: str, available_images: list[str] = None) -> str:
        """
        执行写作任务
        Args:
            prompt: 写作提示
            available_images: 可用的图片列表
        """
        if available_images:
            self.available_images = available_images
            image_list = "\n".join([f"- {img}" for img in available_images])
            image_prompt = (
                f"\n可用的图片列表：\n{image_list}\n请在写作时适当引用这些图片。"
            )
            prompt = prompt + image_prompt

        return super().run(prompt, self.system_prompt)

    def summarize(self) -> str:
        """
        总结对话内容
        """
        try:
            self.append_chat_history(
                {"role": "user", "content": "请简单总结以上完成什么任务取得什么结果:"}
            )
            # 获取历史消息用于本次对话
            response = self.model.chat(
                history=self.chat_history, agent_name=self.__class__.__name__
            )
            self.append_chat_history(
                {"role": "assistant", "content": response.choices[0].message.content}
            )
            return response.choices[0].message.content
        except Exception as e:
            log.error(f"总结生成失败: {str(e)}")
            # 返回一个基础总结，避免完全失败
            return "由于网络原因无法生成详细总结，但已完成主要任务处理。"
