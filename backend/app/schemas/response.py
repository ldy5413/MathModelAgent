from typing import Literal
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
    agent_type: AgentType  # Coder | Writer


class CodeExecutionResult(BaseModel):
    msg_type: str
    msg: str


# 1. 只带 code
# 2. 只带 code result
class CoderMessage(AgentMessage):
    agent_type: AgentType = AgentType.CODER
    code: str | None = None
    code_result: CodeExecutionResult | None = None


class WriterMessage(AgentMessage):
    agent_type: AgentType = AgentType.WRITER
