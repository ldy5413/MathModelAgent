from pydantic import BaseModel
from app.utils.enums import AgentType

class AgentMessage(BaseModel):
    agent_type: AgentType
    content: str

    class Config:
        orm_mode = True

    def model_dump(self):
        return self.dict()

    @classmethod
    def model_validate_json(cls, json_data):
        return cls.parse_raw(json_data)