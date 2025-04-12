import json
from openai import OpenAI
from app.utils.RichPrinter import RichPrinter
from app.utils.log_util import logger
import time
from app.schemas.response import AgentMessage
from app.utils.enums import AgentType
from app.utils.redis_manager import redis_async_client


class LLM:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        data_reacorder,
        task_id: str,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.chat_count = 0
        self.max_tokens: int | None = None  # 添加最大token数限制
        self.data_recorder = data_reacorder
        self.task_id = task_id

    async def chat(
        self,
        history: list = None,
        tools: list = None,
        tool_choice: str = None,
        max_retries: int = 8,  # 添加最大重试次数
        retry_delay: float = 1.0,  # 添加重试延迟
        top_p: float | None = None,  # 添加top_p参数,
        agent_name: str = "NO_NAME",  # CoderAgent or WriterAgent
    ) -> str:
        kwargs = {
            "model": self.model,
            "messages": history,
            "stream": False,
            "top_p": top_p,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens

        # TODO: stream 输出
        for attempt in range(max_retries):
            try:
                completion = self.client.chat.completions.create(**kwargs)
                if not completion or not hasattr(completion, "choices"):
                    raise ValueError("无效的API响应")
                self.chat_count += 1
                await self.analyse_completion(completion, agent_name)
                return completion
            except json.JSONDecodeError:
                logger.error(f"第{attempt + 1}次重试: API返回无效JSON")
                time.sleep(retry_delay * (attempt + 1))
            except Exception as e:
                logger.error(
                    f"API调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
                )
                if attempt < max_retries - 1:  # 如果不是最后一次尝试
                    time.sleep(retry_delay * (attempt + 1))  # 指数退避
                    continue
                logger.debug(f"请求参数: {kwargs}")
                raise  # 如果所有重试都失败，则抛出异常

    async def analyse_completion(self, completion, agent_name: str):
        self.record_data(completion, agent_name)
        await self.print_msg(completion, agent_name)

    def record_data(self, completion, agent_name: str):
        self.data_recorder.append_chat_completion(completion, agent_name)

    async def print_msg(self, completion, agent_name):
        code = ""
        if (
            hasattr(completion.choices[0].message, "tool_calls")
            and completion.choices[0].message.tool_calls
        ):
            tool_call = completion.choices[0].message.tool_calls[0]
            if tool_call.function.name == "execute_code":
                code = json.loads(tool_call.function.arguments)["code"]

        await self.send_message(agent_name, completion.choices[0].message.content, code)

        RichPrinter.print_agent_msg(
            completion.choices[0].message.content + code, agent_name=agent_name
        )
        logger.debug(completion)

    async def send_message(self, agent_name, content, code=None):
        agent_type = AgentType.CODER if agent_name == "CoderAgent" else AgentType.WRITER
        agent_msg = AgentMessage(
            agent_type=agent_type,
            code=code,
            content=content,
        )
        print(f"发送消息: {agent_msg.model_dump_json()}")  # 调试输出

        await self._push_to_websocket(agent_msg)

    async def _push_to_websocket(self, agent_msg: AgentMessage):
        # 将同步方法改为异步方法
        async def _async_push():
            await redis_async_client.publish(
                f"task:{self.task_id}:messages",
                agent_msg.model_dump_json(),
            )

        # 在同步上下文中运行异步任务

        await _async_push()


class DeepSeekModel(LLM):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        task_id: str,
        data_recorder,
    ):
        super().__init__(api_key, model, base_url, data_recorder, task_id)
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
