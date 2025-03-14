from app.utils.enums import AgentType
from pydantic import BaseModel
from typing import Any


class CodeExecutionResult(BaseModel):
    content: list[tuple[str, Any]]
    error: str | None = None


class AgentMessage(BaseModel):
    agent_type: AgentType
    code: str | None = None
    code_result: CodeExecutionResult | None = None
    content: str | None = None
    section: str | None = None
