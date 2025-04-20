from app.utils.enums import AgentType
from pydantic import BaseModel
from typing import Any


class CodeExecutionResult(BaseModel):
    msg_type: str
    msg: str


class AgentMessage(BaseModel):
    agent_type: AgentType
    content: str | None = None


class CoderMessage(AgentMessage):
    agent_type: AgentType = AgentType.CODER
    code: str | None = None
    code_result: CodeExecutionResult | None = None


class WriterMessage(AgentMessage):
    agent_type: AgentType = AgentType.WRITER
