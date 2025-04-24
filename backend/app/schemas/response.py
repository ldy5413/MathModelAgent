from app.utils.enums import AgentType
from pydantic import BaseModel


class AgentMessage(BaseModel):
    agent_type: AgentType
    content: str | None = None


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
