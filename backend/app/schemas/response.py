from app.utils.enums import AgentType
from pydantic import BaseModel


class CodeExecutionResult(BaseModel):
    content: dict[str, str]
    error: str | None = None


class AgentMessage(BaseModel):
    agent_type: AgentType
    code: str | None = None
    code_result: CodeExecutionResult | None = None
    content: str | None = None
    section: str | None = None
