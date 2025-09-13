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
import ast
import textwrap

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

    def _sanitize_code(self, code: str) -> str:
        """基本清洗代码以减少缩进问题：
        - 统一换行
        - 将 TAB 转为 4 空格
        - 去除公共缩进（dedent）
        - 去除首尾空白并保证末尾换行
        """
        if not code:
            return ""
        code2 = code.replace("\r\n", "\n").replace("\r", "\n")
        code2 = code2.expandtabs(4)
        code2 = textwrap.dedent(code2)
        code2 = code2.strip()
        if not code2.endswith("\n"):
            code2 += "\n"
        return code2

    def _syntax_check(self, code: str) -> tuple[bool, str]:
        """使用内置编译器进行语法检查，提前捕获 IndentationError/SyntaxError"""
        try:
            compile(code, "<lint>", "exec")
            return True, ""
        except (SyntaxError, IndentationError) as e:
            # 构造简洁易读的错误信息，并附带出错行内容
            lineno = getattr(e, "lineno", None)
            offset = getattr(e, "offset", None)
            msg = getattr(e, "msg", str(e))
            parts = [f"{e.__class__.__name__}: {msg}"]
            if lineno is not None:
                parts.append(f"at line {lineno}{', col ' + str(offset) if offset else ''}")
                try:
                    line = code.splitlines()[lineno - 1]
                    parts.append(f">> {lineno}: {line}")
                except Exception:
                    pass
            return False, "\n".join(parts)

    def _extract_code_block(self, text: str) -> str | None:
        """从模型回复中提取代码块。

        - 优先收集所有 ```python/py ...``` 代码块
        - 其次收集所有普通 ``` ... ``` 代码块
        - 如找到多个，返回“最长”的那个代码块
        """
        if not text:
            return None

        candidates: list[str] = []

        # 收集显式标注为 python 的代码块
        pattern_lang = re.compile(
            r"```\s*(?:python|py)\s*\n(.*?)```", re.DOTALL | re.IGNORECASE
        )
        for m in pattern_lang.finditer(text):
            code = (m.group(1) or "").strip()
            if code:
                candidates.append(code)

        # 收集不带语言标注的三引号代码块
        pattern_any = re.compile(r"```\s*\n(.*?)```", re.DOTALL)
        for m in pattern_any.finditer(text):
            code = (m.group(1) or "").strip()
            if code:
                candidates.append(code)

        if not candidates:
            return None

        # 返回最长的代码块
        return max(candidates, key=len)

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

                # 统一处理：放宽工具名匹配 + 任意含 code 参数的 function 调用都执行
                tool_name = getattr(tool_call.function, "name", "") or ""
                raw_args = getattr(tool_call.function, "arguments", "") or ""

                accepted_names = {"execute_code", "exec_code", "run_code", "python", "code", "execute"}

                def _parse_code_from_args(args_str: str, assistant_text: str) -> str | None:
                    # 1) 优先 JSON 解析
                    try:
                        data = json.loads(args_str)
                        if isinstance(data, dict) and isinstance(data.get("code"), str):
                            return data["code"].strip()
                    except Exception:
                        pass
                    # 2) 从参数字符串中提取代码块
                    code2 = self._extract_code_block(args_str)
                    if code2:
                        return code2
                    # 3) 回退：从助手正文中提取
                    return self._extract_code_block(assistant_text)

                # 更新对话历史 - 添加助手的响应（包含实际的 tool_calls）
                await self.append_chat_history(response.choices[0].message.model_dump())
                logger.info(response.choices[0].message.model_dump())

                code: str | None = None
                if tool_name in accepted_names:
                    code = _parse_code_from_args(raw_args, response.choices[0].message.content or "")
                    await redis_manager.publish_message(
                        self.task_id,
                        SystemMessage(content=f"代码手调用{tool_name}工具"),
                    )
                else:
                    # 未知的工具名：尝试按 execute_code 解析处理，并通知前端
                    await redis_manager.publish_message(
                        self.task_id,
                        SystemMessage(content=f"检测到未知工具名: {tool_name}，尝试按 execute_code 解析并执行"),
                    )
                    code = _parse_code_from_args(raw_args, response.choices[0].message.content or "")

                if code:
                    # 预处理与语法检查（提前拦截缩进/语法错误）
                    sanitized_code = self._sanitize_code(code)
                    ok, lint_err = self._syntax_check(sanitized_code)
                    if not ok:
                        # 记录并引导反思，而不是直接执行
                        await self.append_chat_history(
                            {
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "name": "execute_code",
                                "content": lint_err,
                            }
                        )

                        await redis_manager.publish_message(
                            self.task_id,
                            SystemMessage(content=f"预执行语法检查失败，已跳过执行并触发反思\n{lint_err}", type="error"),
                        )

                        retry_count += 1
                        last_error_message = lint_err
                        reflection_prompt = get_reflection_prompt(lint_err, code)
                        await self.append_chat_history(
                            {"role": "user", "content": reflection_prompt}
                        )
                        continue

                    # 通知前端将要执行的代码
                    await redis_manager.publish_message(
                        self.task_id,
                        InterpreterMessage(input={"code": sanitized_code}),
                    )

                    logger.info("执行工具调用/兼容解析得到的代码…")
                    (
                        text_to_gpt,
                        error_occurred,
                        error_message,
                    ) = await self.code_interpreter.execute_code(sanitized_code)

                    # 记录执行结果到历史（使用原 tool_call_id 以保持配对）
                    if error_occurred:
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
                        continue
                    else:
                        await self.append_chat_history(
                            {
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "name": "execute_code",
                                "content": text_to_gpt,
                            }
                        )
                        # 继续下一轮
                        continue
                else:
                    # 未能从工具参数/正文提取代码，触发回退提示 -> 再尝试从助手正文提取并执行
                    await redis_manager.publish_message(
                        self.task_id,
                        SystemMessage(content=f"工具名 {tool_name} 无法解析出代码，回退到从回复中提取代码"),
                    )
                    assistant_content = response.choices[0].message.content or ""
                    code_block2 = self._extract_code_block(assistant_content)
                    if code_block2:
                        # 预处理与语法检查（提前拦截缩进/语法错误）
                        sanitized_code2 = self._sanitize_code(code_block2)
                        ok2, lint_err2 = self._syntax_check(sanitized_code2)
                        if not ok2:
                            await self.append_chat_history(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_id,
                                    "name": "execute_code",
                                    "content": lint_err2,
                                }
                            )

                            await redis_manager.publish_message(
                                self.task_id,
                                SystemMessage(content=f"预执行语法检查失败，已跳过执行并触发反思\n{lint_err2}", type="error"),
                            )
                            retry_count += 1
                            last_error_message = lint_err2
                            reflection_prompt = get_reflection_prompt(
                                lint_err2, code_block2
                            )
                            await self.append_chat_history(
                                {"role": "user", "content": reflection_prompt}
                            )
                            continue

                        await redis_manager.publish_message(
                            self.task_id,
                            InterpreterMessage(input={"code": sanitized_code2}),
                        )
                        (
                            text_to_gpt,
                            error_occurred,
                            error_message,
                        ) = await self.code_interpreter.execute_code(sanitized_code2)
                        if error_occurred:
                            await self.append_chat_history(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_id,
                                    "name": "execute_code",
                                    "content": error_message,
                                }
                            )
                            logger.warning(f"回退代码执行错误: {error_message}")
                            retry_count += 1
                            last_error_message = error_message
                            reflection_prompt = get_reflection_prompt(
                                error_message, code_block2
                            )
                            await self.append_chat_history(
                                {"role": "user", "content": reflection_prompt}
                            )
                            continue
                        else:
                            await self.append_chat_history(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_id,
                                    "name": "execute_code",
                                    "content": text_to_gpt,
                                }
                            )
                            continue
                    else:
                        # 给模型一个明确提示以产出正确的工具调用
                        guidance = (
                            "请调用名为 execute_code 的 function 工具，并传入严格 JSON 形如 {\"code\": \"...\"}（仅包含 code 字段）。"
                        )
                        await self.append_chat_history(
                            {"role": "user", "content": guidance}
                        )
                        continue
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

                    # 预处理与语法检查（提前拦截缩进/语法错误）
                    sanitized_code3 = self._sanitize_code(code_block)
                    ok3, lint_err3 = self._syntax_check(sanitized_code3)
                    if not ok3:
                        await self.append_chat_history(
                            {
                                "role": "tool",
                                "tool_call_id": synthetic_tool_id,
                                "name": "execute_code",
                                "content": lint_err3,
                            }
                        )

                        await redis_manager.publish_message(
                            self.task_id,
                            SystemMessage(content=f"预执行语法检查失败，已跳过执行并触发反思\n{lint_err3}", type="error"),
                        )

                        retry_count += 1
                        logger.info(f"当前尝试次:{retry_count} / {self.max_retries}")
                        last_error_message = lint_err3
                        reflection_prompt = get_reflection_prompt(
                            lint_err3, code_block
                        )

                        await self.append_chat_history(
                            {"role": "user", "content": reflection_prompt}
                        )
                        # 继续循环，让模型基于错误进行反思修复
                        continue

                    # 通知前端将要执行的代码
                    await redis_manager.publish_message(
                        self.task_id,
                        InterpreterMessage(
                            input={"code": sanitized_code3},
                        ),
                    )

                    # 执行代码
                    logger.info("回退执行代码中…")
                    (
                        text_to_gpt,
                        error_occurred,
                        error_message,
                    ) = await self.code_interpreter.execute_code(sanitized_code3)

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
