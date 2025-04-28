from typing import List, Literal, Union
from app.utils.enums import AgentType
from pydantic import BaseModel, Field
from uuid import uuid4


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    msg_type: Literal["system", "agent"] | None  # system msg | agent messsage
    content: str | None = None


class SystemMessage(Message):
    msg_type: str = "system"
    type: Literal["info", "warning", "success", "error"] = "info"


class AgentMessage(Message):
    msg_type: str = "agent"
    agent_type: AgentType  # CoderAgent | WriterAgent


class CodeExecution(BaseModel):
    res_type: Literal["stdout", "stderr", "result", "error"]
    msg: str | None = None


class StdOutModel(CodeExecution):
    res_type: str = "stdout"


class StdErrModel(CodeExecution):
    res_type: str = "stderr"


class ResultModel(CodeExecution):
    res_type: str = "result"
    format: Literal[
        "text",
        "html",
        "markdown",
        "png",
        "jpeg",
        "svg",
        "pdf",
        "latex",
        "json",
        "javascript",
    ]


class ErrorModel(CodeExecution):
    res_type: str = "error"
    name: str
    value: str
    traceback: str


# 总返回类型
OutputItem = Union[StdOutModel, StdErrModel, ResultModel, ErrorModel]


# 1. 只带 code
# 2. 只带 code result
class CoderMessage(AgentMessage):
    agent_type: AgentType = AgentType.CODER
    code: str | None = None
    code_results: list[OutputItem] | None = None


class WriterMessage(AgentMessage):
    agent_type: AgentType = AgentType.WRITER
