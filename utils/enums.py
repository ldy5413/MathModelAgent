from enum import Enum


class CompTemplate(Enum):
    CHINA: str = "国赛"
    AMERICAN: str = "美赛"


class FormatOutPut(Enum):
    Markdown: str = "Markdown"
    LaTeX: str = "LaTeX"
