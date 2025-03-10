from pydantic import BaseModel
from app.utils.enums import CompTemplate, FormatOutPut


class Problem(BaseModel):
    task_id: str
    ques_all: str = ""
    comp_template: CompTemplate = CompTemplate.CHINA
    format_output: FormatOutPut = FormatOutPut.Markdown
