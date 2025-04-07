import json
from app.core.LLM import LLM
from app.core.prompts import get_writer_prompt, CODER_PROMPT, MODELER_PROMPT
from app.core.functions import tools
from app.models.user_output import UserOutput
from app.tools.code_interpreter import E2BCodeInterpreter
from app.utils.common_utils import get_current_files
from app.utils.enums import CompTemplate, FormatOutPut
from app.utils.logger import log
from app.utils.RichPrinter import RichPrinter
from app.config.config import settings
from app.utils.notebook_serializer import NotebookSerializer


class Agent:
    def __init__(
        self,
        model: LLM,
        max_chat_turns: int = 30,  # 单个agent最大对话轮次
        user_output: UserOutput = None,
    ) -> None:
        self.model = model
        self.chat_history: list[dict] = []  # 存储对话历史
        self.max_chat_turns = max_chat_turns  # 最大对话轮次
        self.current_chat_turns = 0  # 当前对话轮次计数器
        self.user_output = user_output

    async def run(self, prompt: str, system_prompt: str) -> str:
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
            response = await self.model.chat(
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
        model: LLM,
        max_chat_turns: int = 30,  # 添加最大对话轮次限制
    ) -> None:
        super().__init__(model, max_chat_turns)
        self.system_prompt = MODELER_PROMPT


# 代码强
class CoderAgent(Agent):  # 同样继承自Agent类
    def __init__(
        self,
        model: LLM,
        dirs: dict,  # 工作目录
        max_chat_turns: int = settings.MAX_CHAT_TURNS,  # TODO: 配置文件
        max_retries: int = settings.MAX_RETRIES,  # 重试次数
        user_output: UserOutput = None,
        task_id: str = None,
    ) -> None:
        super().__init__(model, max_chat_turns, user_output)
        self.dirs = dirs
        self.notebook_serializer = NotebookSerializer(dirs["jupyter"])
        self.code_interpreter = E2BCodeInterpreter(
            dirs, task_id, self.notebook_serializer
        )

        self.max_retries = max_retries
        self.is_first_run = True
        self.system_prompt = CODER_PROMPT

    async def run(self, prompt: str, subtask_title: str) -> str:
        RichPrinter.agent_start(self.__class__.__name__)

        self.notebook_serializer.add_markdown_segmentation_to_notebook(
            content=prompt, segmentation=subtask_title
        )
        self.code_interpreter.add_section(subtask_title)

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

            # try:
        while (
            not task_completed
            and retry_count < self.max_retries
            and self.current_chat_turns < self.max_chat_turns
        ):
            self.current_chat_turns += 1
            response = await self.model.chat(
                history=self.chat_history,
                tools=tools,
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

                    # 执行工具调用
                    (
                        text_to_gpt,
                        _,
                        error_occurred,
                        error_message,
                    ) = await self.code_interpreter.execute_code(code)

                    # 记录执行结果

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
                        reflection_prompt = f"""The code execution encountered an error:
{error_message}

Please analyze the error, identify the cause, and provide a corrected version of the code. 
Consider:
1. Syntax errors
2. Missing imports
3. Incorrect variable names or types
4. File path issues
5. Any other potential issues
6. 如果一个任务反复无法完成，尝试切换路径、简化路径，千万别陷入反复重试，导致死循环。

Previous code:
{code}

Please provide an explanation of what went wrong and the corrected code."""

                        self.append_chat_history(
                            {"role": "user", "content": reflection_prompt}
                        )
                        continue

                    # 检查任务完成情况时也计入对话轮次
                    self.current_chat_turns += 1
                    # 使用π所有执行结果生成检查提示
                    completion_check_prompt = f"""
Please analyze the current state and determine if the task is fully completed:

Original task: {prompt}

Latest execution results:
{text_to_gpt}  # 修改：使用合并后的结果

Consider:
1. Have all required data processing steps been completed?
2. Have all necessary files been saved?
3. Are there any remaining steps needed?
4. Is the output satisfactory and complete?
5. 如果一个任务反复无法完成，尝试切换路径、简化路径或直接跳过，千万别陷入反复重试，导致死循环。
6. 尽量在较少的对话轮次内完成任务，task_completed = True
If the task is not complete, please explain what remains to be done and continue with the next steps.
If the task is complete, please provide a summary of what was accomplished about your create image name.
"""
                    self.append_chat_history(
                        {"role": "user", "content": completion_check_prompt}
                    )

                    completion_response = await self.model.chat(
                        history=self.chat_history,
                        tools=tools,
                        tool_choice="auto",
                        agent_name=self.__class__.__name__,
                    )

                    # # TODO: 压缩对话历史

                    if not (
                        hasattr(completion_response.choices[0].message, "tool_calls")
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
        return response.choices[0].message.content

    def get_notebook_serializer(self) -> NotebookSerializer:
        """获取notebook序列化器"""
        return self.notebook_serializer


# 长文本
# TODO: 并行 parallel
class WriterAgent(Agent):  # 同样继承自Agent类
    def __init__(
        self,
        model: LLM,
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

    async def summarize(self) -> str:
        """
        总结对话内容
        """
        try:
            self.append_chat_history(
                {"role": "user", "content": "请简单总结以上完成什么任务取得什么结果:"}
            )
            # 获取历史消息用于本次对话
            response = await self.model.chat(
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
