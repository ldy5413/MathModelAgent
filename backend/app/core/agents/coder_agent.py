from app.core.agents.agent import Agent
from app.config.setting import settings
from app.utils.log_util import logger
from app.services.redis_manager import redis_manager
from app.schemas.response import SystemMessage, InterpreterMessage
from app.tools.base_interpreter import BaseCodeInterpreter
from app.core.llm.llm import LLM
from app.schemas.A2A import CoderToWriter
from app.core.prompts import CODER_PROMPT
from app.utils.common_utils import get_current_files
import json
from app.core.prompts import get_reflection_prompt, get_completion_check_prompt
from app.core.functions import coder_tools
from icecream import ic
import re
import uuid

# TODO: 时间等待过久，stop 进程
# TODO: 支持 cuda
# TODO: 引入创新方案：


# 代码强
class CoderAgent(Agent):  # 同样继承自Agent类
    def __init__(
        self,
        task_id: str,
        model: LLM,
        work_dir: str,  # 工作目录
        max_chat_turns: int = settings.MAX_CHAT_TURNS,  # 最大聊天次数
        max_retries: int = settings.MAX_RETRIES,  # 最大反思次数
        code_interpreter: BaseCodeInterpreter = None,
    ) -> None:
        super().__init__(task_id, model, max_chat_turns)
        self.work_dir = work_dir
        self.max_retries = max_retries
        self.is_first_run = True
        self.system_prompt = CODER_PROMPT
        self.code_interpreter = code_interpreter

    def _extract_code_block(self, text: str) -> str | None:
        """从模型回复中提取 Python 代码块。

        优先匹配 ```python/py ...```，其次回退到任意 ``` ... ```。
        找到多个时取第一个。
        """
        if not text:
            return None

        # 优先匹配显式标注为 python 的代码块
        pattern_lang = re.compile(r"```\s*(?:python|py)\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
        m = pattern_lang.search(text)
        if m and m.group(1).strip():
            return m.group(1).strip()

        # 回退匹配任意三引号代码块
        pattern_any = re.compile(r"```\s*\n(.*?)```", re.DOTALL)
        m = pattern_any.search(text)
        if m and m.group(1).strip():
            return m.group(1).strip()

        return None

    async def run(self, prompt: str, subtask_title: str) -> CoderToWriter:
        logger.info(f"{self.__class__.__name__}:开始:执行子任务: {subtask_title}")
        self.code_interpreter.add_section(subtask_title)

        # 如果是第一次运行，则添加系统提示
        if self.is_first_run:
            logger.info("首次运行，添加系统提示和数据集文件信息")
            self.is_first_run = False
            await self.append_chat_history(
                {"role": "system", "content": self.system_prompt}
            )
            # 当前数据集文件
            await self.append_chat_history(
                {
                    "role": "user",
                    "content": f"当前文件夹下的数据集文件{get_current_files(self.work_dir, 'data')}",
                }
            )

        # 添加 sub_task
        logger.info(f"添加子任务提示: {prompt}")
        await self.append_chat_history({"role": "user", "content": prompt})

        retry_count = 0
        last_error_message = ""

        if self.current_chat_turns >= self.max_chat_turns:
            logger.error(f"超过最大聊天次数: {self.max_chat_turns}")
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content="超过最大聊天次数", type="error"),
            )
            raise Exception(
                f"Reached maximum number of chat turns ({self.max_chat_turns}). Task incomplete."
            )

        if retry_count >= self.max_retries:
            logger.error(f"超过最大尝试次数: {self.max_retries}")
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content="超过最大尝试次数", type="error"),
            )
            raise Exception(
                f"Failed to complete task after {self.max_retries} attempts. Last error: {last_error_message}"
            )

        # try:
        while (
            retry_count < self.max_retries
            and self.current_chat_turns < self.max_chat_turns
        ):
            self.current_chat_turns += 1
            logger.info(f"当前对话轮次: {self.current_chat_turns}")
            response = await self.model.chat(
                history=self.chat_history,
                tools=coder_tools,
                tool_choice="auto",
                agent_name=self.__class__.__name__,
            )

            # 如果有工具调用
            if (
                hasattr(response.choices[0].message, "tool_calls")
                and response.choices[0].message.tool_calls
            ):
                logger.info("检测到工具调用")
                tool_call = response.choices[0].message.tool_calls[0]
                tool_id = tool_call.id
                # TODO: json JSON解析时遇到了无效的转义字符
                if tool_call.function.name == "execute_code":
                    logger.info(f"调用工具: {tool_call.function.name}")
                    await redis_manager.publish_message(
                        self.task_id,
                        SystemMessage(
                            content=f"代码手调用{tool_call.function.name}工具"
                        ),
                    )

                    code = json.loads(tool_call.function.arguments)["code"]

                    await redis_manager.publish_message(
                        self.task_id,
                        InterpreterMessage(
                            input={"code": code},
                        ),
                    )

                    # 更新对话历史 - 添加助手的响应
                    await self.append_chat_history(
                        response.choices[0].message.model_dump()
                    )
                    logger.info(response.choices[0].message.model_dump())

                    # 执行工具调用
                    logger.info("执行工具调用")
                    (
                        text_to_gpt,
                        error_occurred,
                        error_message,
                    ) = await self.code_interpreter.execute_code(code)

                    # 添加工具执行结果
                    if error_occurred:
                        # 即使发生错误也要添加tool响应
                        await self.append_chat_history(
                            {
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "name": "execute_code",
                                "content": error_message,
                            }
                        )

                        logger.warning(f"代码执行错误: {error_message}")
                        retry_count += 1
                        logger.info(f"当前尝试次:{retry_count} / {self.max_retries}")
                        last_error_message = error_message
                        reflection_prompt = get_reflection_prompt(error_message, code)

                        await redis_manager.publish_message(
                            self.task_id,
                            SystemMessage(content="代码手反思纠正错误", type="error"),
                        )

                        await self.append_chat_history(
                            {"role": "user", "content": reflection_prompt}
                        )
                        # 如果代码出错，返回重新开始
                        continue
                    else:
                        # 成功执行的tool响应
                        await self.append_chat_history(
                            {
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "name": "execute_code",
                                "content": text_to_gpt,
                            }
                        )
            else:
                # 无工具调用，尝试回退：从回复中提取代码并执行
                assistant_content = response.choices[0].message.content or ""
                code_block = self._extract_code_block(assistant_content)

                if code_block:
                    logger.info("未返回 tool_calls，触发回退：从回复中提取到代码块并执行")
                    await redis_manager.publish_message(
                        self.task_id,
                        SystemMessage(content="触发回退：从回复中提取代码并执行"),
                    )

                    # 生成一个合成的 tool_call id，并把 assistant 回复作为带有 tool_calls 的消息加入历史
                    synthetic_tool_id = f"fallback_{uuid.uuid4()}"
                    synthetic_assistant_msg = {
                        "role": "assistant",
                        "content": assistant_content,
                        "tool_calls": [
                            {
                                "id": synthetic_tool_id,
                                "type": "function",
                                "function": {
                                    "name": "execute_code",
                                    "arguments": json.dumps({"code": code_block}),
                                },
                            }
                        ],
                    }
                    await self.append_chat_history(synthetic_assistant_msg)

                    # 通知前端将要执行的代码
                    await redis_manager.publish_message(
                        self.task_id,
                        InterpreterMessage(
                            input={"code": code_block},
                        ),
                    )

                    # 执行代码
                    logger.info("回退执行代码中…")
                    (
                        text_to_gpt,
                        error_occurred,
                        error_message,
                    ) = await self.code_interpreter.execute_code(code_block)

                    # 记录执行结果到历史，作为 tool 响应（与上面的合成 tool_call 匹配）
                    if error_occurred:
                        await self.append_chat_history(
                            {
                                "role": "tool",
                                "tool_call_id": synthetic_tool_id,
                                "name": "execute_code",
                                "content": error_message,
                            }
                        )

                        logger.warning(f"回退代码执行错误: {error_message}")
                        retry_count += 1
                        logger.info(f"当前尝试次:{retry_count} / {self.max_retries}")
                        last_error_message = error_message
                        reflection_prompt = get_reflection_prompt(
                            error_message, code_block
                        )

                        await redis_manager.publish_message(
                            self.task_id,
                            SystemMessage(content="代码手反思纠正错误", type="error"),
                        )

                        await self.append_chat_history(
                            {"role": "user", "content": reflection_prompt}
                        )
                        # 继续循环，让模型基于错误进行反思修复
                        continue
                    else:
                        await self.append_chat_history(
                            {
                                "role": "tool",
                                "tool_call_id": synthetic_tool_id,
                                "name": "execute_code",
                                "content": text_to_gpt,
                            }
                        )
                        # 继续循环，让模型基于执行结果进行后续思考
                        continue
                else:
                    # 未提取到代码块，按任务完成处理
                    logger.info("没有工具调用且未检测到代码块，判定任务完成")
                    return CoderToWriter(
                        coder_response=assistant_content,
                        created_images=await self.code_interpreter.get_created_images(
                            subtask_title
                        ),
                    )

            if retry_count >= self.max_retries:
                logger.error(f"超过最大尝试次数: {self.max_retries}")
                return f"Failed to complete task after {self.max_retries} attempts. Last error: {last_error_message}"

            if self.current_chat_turns >= self.max_chat_turns:
                logger.error(f"超过最大对话轮次: {self.max_chat_turns}")
                return f"Reached maximum number of chat turns ({self.max_chat_turns}). Task incomplete."

        logger.info(f"{self.__class__.__name__}:完成:执行子任务: {subtask_title}")

        return CoderToWriter(
            coder_response=response.choices[0].message.content,
            created_images=await self.code_interpreter.get_created_images(
                subtask_title
            ),
        )
