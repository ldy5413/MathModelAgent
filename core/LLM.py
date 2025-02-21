import json
from openai import OpenAI
from utils.RichPrinter import RichPrinter
from utils.logger import log
import time


class BaseModel:
    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.chat_count = 0
        self.max_tokens: int | None = None  # 添加最大token数限制

    def chat(
        self,
        history: list = None,
        tools: list = None,
        tool_choice: str = None,
        max_retries: int = 8,  # 添加最大重试次数
        retry_delay: float = 1.0,  # 添加重试延迟
        top_p: float | None = None,  # 添加top_p参数,
        agent_name: str = "NO_NAME",
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
        from utils.io import output_content

        output_content.data_recorder.append_chat_completion(completion, agent_name)

    def print_msg(self, completion, agent_name):
        code = ""
        if (
            hasattr(completion.choices[0].message, "tool_calls")
            and completion.choices[0].message.tool_calls
        ):
            tool_call = completion.choices[0].message.tool_calls[0]
            if tool_call.function.name == "execute_code":
                code = json.loads(tool_call.function.arguments)["code"]

        RichPrinter.print_agent_msg(
            completion.choices[0].message.content + code, agent_name=agent_name
        )
        log.debug(completion)


class DeepSeekModel(BaseModel):
    def __init__(self, api_key: str, model: str, base_url: str):
        super().__init__(api_key, model, base_url)
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
