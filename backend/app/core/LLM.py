import json
from openai import OpenAI
from app.utils.RichPrinter import RichPrinter
from app.utils.logger import log
import time
from app.schemas.response import AgentMessage
from app.utils.enums import AgentType
from app.main import redis_async_client


class LLM:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        data_reacorder,
        message_queue,
        task_id: str,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.chat_count = 0
        self.max_tokens: int | None = None  # 添加最大token数限制
        self.data_recorder = data_reacorder
        self.message_queue = message_queue
        self.task_id = task_id

    def chat(
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
                self.analyse_completion(completion, agent_name)
                return completion
            except json.JSONDecodeError:
                log.error(f"第{attempt + 1}次重试: API返回无效JSON")
                time.sleep(retry_delay * (attempt + 1))
            except Exception as e:
                log.error(f"API调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:  # 如果不是最后一次尝试
                    time.sleep(retry_delay * (attempt + 1))  # 指数退避
                    continue
                log.debug(f"请求参数: {kwargs}")
                raise  # 如果所有重试都失败，则抛出异常

    def analyse_completion(self, completion, agent_name: str):
        self.record_data(completion, agent_name)
        self.print_msg(completion, agent_name)

    def record_data(self, completion, agent_name: str):
        self.data_recorder.append_chat_completion(completion, agent_name)

    def print_msg(self, completion, agent_name):
        code = ""
        if (
            hasattr(completion.choices[0].message, "tool_calls")
            and completion.choices[0].message.tool_calls
        ):
            tool_call = completion.choices[0].message.tool_calls[0]
            if tool_call.function.name == "execute_code":
                code = json.loads(tool_call.function.arguments)["code"]

        self.send_message(agent_name, completion.choices[0].message.content, code)

        RichPrinter.print_agent_msg(
            completion.choices[0].message.content + code, agent_name=agent_name
        )
        log.debug(completion)

    def send_message(self, agent_name, content, code=None):
        agent_type = AgentType.CODER if agent_name == "CoderAgent" else AgentType.WRITER
        agent_msg = AgentMessage(
            agent_type=agent_type,
            code=code,
            content=content,
        )
        print(f"发送消息: {agent_msg.model_dump_json()}")  # 调试输出

        if self.message_queue:
            self.message_queue.put(agent_msg)

        self._push_to_websocket(agent_msg)

    def _push_to_websocket(self, agent_msg: AgentMessage):
        redis_async_client.publish(
            f"task:{self.task_id}:messages",
            agent_msg.model_dump_json(),
        )


class DeepSeekModel(LLM):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        task_id: str,
        data_recorder,
        message_queue,
    ):
        super().__init__(
            api_key, model, base_url, data_recorder, message_queue, task_id
        )
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
