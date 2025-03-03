from pydantic import BaseModel


class Problem(BaseModel):
    task_id: str = None
    ques: str = ""
