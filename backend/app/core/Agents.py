import json
from app.core.LLM import LLM
from app.models.user_output import UserOutput
from app.tools.code_interpreter import E2BCodeInterpreter
from app.utils.common_utils import get_current_files
from app.utils.enums import CompTemplate, FormatOutPut
from app.utils.logger import log
from app.utils.RichPrinter import RichPrinter
from app.config.config import settings

functions = [
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "This function allows you to execute Python code and retrieve the terminal output. If the code "
            "generates image output, the function will return the text '[image]'. The code is sent to a "
            "Jupyter kernel for execution. The kernel will remain active after execution, retaining all "
            "variables in memory."
            "You cannot show rich outputs like plots or images, but you can store them in the working directory and point the user to them. ",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The code text"}
                },
                "required": ["code"],
                "additionalProperties": False,
            },
        },
    },
]


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
        model: LLM,
        max_chat_turns: int = 30,  # 添加最大对话轮次限制
    ) -> None:
        super().__init__(model, max_chat_turns)
        self.system_prompt = """
        role：你是一名数学建模经验丰富的建模手，负责建模部分。
        task：你需要根据用户要求和数据建立数学模型求解问题。
        skill：熟练掌握各种数学建模的模型和思路
        output：数学建模的思路和使用到的模型
        attention：不需要给出代码，只需要给出思路和模型
        **不需要建立复杂的模型,简单规划需要步骤**
        """


# 代码强
class CoderAgent(Agent):  # 同样继承自Agent类
    def __init__(
        self,
        model: LLM,
        work_dir: str,  # 工作目录
        max_chat_turns: int = settings.MAX_CHAT_TURNS,  # TODO: 配置文件
        max_retries: int = settings.MAX_RETRIES,  # 重试次数
        user_output: UserOutput = None,
        task_id: str = None,
    ) -> None:
        super().__init__(model, max_chat_turns, user_output)
        self.work_dir = work_dir
        self.code_interpreter = E2BCodeInterpreter(work_dir, task_id)

        self.max_retries = max_retries
        self.is_first_run = True
        self.created_images: list[str] = []  # 当前任务创建的图片列表
        self.system_prompt = """You are an AI code interpreter.
Your goal is to help users do a variety of jobs by executing Python code.

When generating code:
1. Use double quotes for strings containing Chinese characters
2. Do not use Unicode escape sequences for Chinese characters
3. Write Chinese characters directly in the string

For example:
# Correct:
df["婴儿行为特征"] = "矛盾型"

# Incorrect:
df['\\u5a74\\u513f\\u884c\\u4e3a\\u7279\\u5f81'] = '\\u77db\\u76df\\u578b'

You should:
1. Comprehend the user's requirements carefully & to the letter.
2. Give a brief description for what you plan to do & call the provided function to run code.
3. Provide results analysis based on the execution output.
4. Check if the task is completed:
   - Verify all required outputs are generated
   - Ensure data processing steps are completed
   - Confirm files are saved as requested
5. If task is incomplete or error occurred:
   - Analyze the current state
   - Identify what's missing or wrong
   - Plan next steps
   - Continue execution until completion
6. 你有能力在较少的步骤中完成任务，减少下一步操作和编排的任务轮次
7. 如果一个任务反复无法完成，尝试切换路径、简化路径或直接跳过，千万别陷入反复重试，导致死循环。
8. Response in the same language as the user.
9. Remember save the output image to the working directory.
10. Remember to **print** the model evaluation results
11. 保存的图片名称需要语义化，方便用户理解
12. 在生成代码时，对于包含单引号的字符串，请使用双引号包裹，避免使用转义字符
13. **你尽量在较少的对话轮次内完成任务。减少反复思考的次数**
14. 在求解问题和建立模型过程中，适当的进行可视化。
15 在画图时候，matplotlib 需要正确显示中文，避免乱码问题。
Note: If the user uploads a file, you will receive a system message "User uploaded a file: filename". Use the filename as the path in the code."""

        self.created_images: list[str] = []  # 当前求解创建的图片

    def run(self, prompt: str, subtask_title: str) -> str:
        RichPrinter.agent_start(self.__class__.__name__)
        self.created_images.clear()  # 清空上一次任务的图片列表
        # TODO: jupyter 的notebook 分节
        # self.notebook_serializer.add_markdown_segmentation_to_notebook(
        # content=prompt, segmentation=subtask_title
        # )

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
                        completion_check_prompt = f"""
Please analyze the current state and determine if the task is fully completed:

Original task: {prompt}

Latest execution result:
{text_to_gpt}

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
        self.system_prompt = f"""
        role：你是一名数学建模经验丰富的写作手，负责写作部分。
        task: 根据问题和如下的模板写出解答,
        skill：熟练掌握{format_output}排版,
        output：你需要按照要求的格式排版,只输出{format_output}排版的内容
        
        1. 当你输入图像引用时候，你需要将用户输入的文件名称路径切换为相对路径
        如用户输入文件路径image_name.png,你转化为../jupyter/image_name.png,就可正确引用显示
        2. 你不需要输出markdown的这个```markdown格式，只需要输出markdown的内容
        3. 严格按照参考用户输入的格式模板以及**正确的编号顺序**
        4. 不需要询问用户
        5. 当提到图片时，请使用提供的图片列表中的文件名
        """
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
