import json
from enum import Enum
from textwrap import dedent
import os
import questionary
from utils.common_utils import simple_chat
from core.LLM import BaseModel
from utils.logger import log


class Template(Enum):
    CHINA = "国赛"
    AMERICAN = "美赛"


class FormatOutPut(Enum):
    Markdown = "Markdown"
    LaTeX = "LaTeX"


class UserInput:
    def __init__(
        self,
        choice: Template = Template.CHINA,
        format_out_put: FormatOutPut = FormatOutPut.Markdown,
        data_folder_path: str = "",
        bg_ques_all: str = "",
        model: BaseModel = None,  # TODO: 不同任务选择不同模型
        init_with_llm: bool = True,  # 新增参数控制是否使用LLM初始化问题
    ):
        self.choice: Template = choice  # 选择模板
        self.format_out_put: FormatOutPut = format_out_put  # 选择输出格式
        self.data_folder_path: str = (
            data_folder_path  # 数据集存放的文件夹 E:\MathModelAgent\project\sample_data
        )
        self.bg_ques_all: str = bg_ques_all  # 用户输入的完整背景以及问题
        self.model: BaseModel = model  # 模型
        self.ques_count: int = 0  # 问题数量
        self.questions: dict[str, str | int] = {}  # 问题
        if init_with_llm:
            self.init_questions()

    def init_questions(self) -> None:
        """用户输入问题 使用LLM 格式化 questions"""
        # TODO:  "note": <补充说明,如果没有补充说明，请填 null>,

        history = [
            {
                "role": "system",
                "content": """
用户将提供给你一段题目信息，**请你不要更改题目信息，完整将用户输入的内容**，以 JSON 的形式输出，输出的 JSON 需遵守以下的格式：

{
  "title": <题目标题>      
  "background": <题目背景，用户输入的一切不在title，ques1，ques2，ques3...中的内容都视为问题背景信息background>,
  "ques_count": <问题数量,number,int>,
  "ques1": <问题1>,
  "ques2": <问题2>,
  "ques3": <问题3,用户输入的存在多少问题，就输出多少问题ques1,ques2,ques3...以此类推>,
}
""",
            },
            {"role": "user", "content": self.bg_ques_all},
        ]
        json_str = simple_chat(self.model, history)
        json_str = json_str.replace("```json", "").replace("```", "").strip()
        log.info(f"json_str: {json_str}\n\n")
        # 检查返回的 JSON 字符串是否有效

        if not json_str:
            raise ValueError("返回的 JSON 字符串为空，请检查输入内容。")

        try:
            self.questions = json.loads(json_str)
            self.ques_count = self.questions["ques_count"]
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析错误: {e}")

    def set_questions_directly(self, questions: dict[str, str | int]) -> None:
        """直接设置questions,跳过LLM请求"""
        self.questions = questions
        self.ques_count = questions.get("ques_count", 0)

    def get_ques_count(self):
        return self.ques_count

    def get_choice(self):
        return self.choice

    def set_choice(self, choice):
        self.choice = choice

    def get_bg_ques_all(self):
        return self.bg_ques_all

    def get_format_out_put(self):
        return self.format_out_put

    def set_format_out_put(self, format_out_put):
        self.format_out_put = format_out_put

    def get_data_folder_path(self):
        return self.data_folder_path

    def set_data_folder_path(self, data_folder_path):
        self.data_folder_path = data_folder_path

    def get_questions(self):
        return self.questions

    def set_questions(self, questions):
        self.questions = questions

    def get_questions_quesx(self) -> dict[str, str]:
        """获取问题1,2,3...的键值对"""
        # 获取所有以 "ques" 开头的键值对
        questions_quesx = {
            key: value
            for key, value in self.questions.items()
            if key.startswith("ques") and key != "ques_count"
        }
        return questions_quesx

    def get_questions_quesx_keys(self) -> list[str]:
        """获取问题1,2...的键"""
        return list(self.get_questions_quesx().keys())

    def __str__(self):
        return f"choice: {self.choice}, format_out_put: {self.format_out_put}, data_folder_path: {self.data_folder_path}, bg_ques_all: {self.bg_ques_all}, model: {self.model}, ques_count: {self.ques_count}, questions: {self.questions}"


def set_user_input_from_cli(model: BaseModel) -> UserInput:
    from utils.io import input_content

    """获取用户输入"""
    print(get_ascii_banner())
    # TODO: 完善：更美观style，错误处理validate，questionary.path
    answers = questionary.form(
        template=questionary.select(
            "选择你需要的模板(目前只支持中文)",
            choices=[
                questionary.Choice(template.value, value=template)
                for template in Template
            ],
            default=Template.CHINA,
        ),
        format_out_put=questionary.select(
            "选择你需要的输出格式(目前只支持markdown)",
            choices=[
                questionary.Choice(format_op.value, value=format_op)
                for format_op in FormatOutPut
            ],
            default=FormatOutPut.Markdown,
        ),
        # TODO: 完善验证：数据集路径
        data_folder_path=questionary.path(
            r"输入输入数据集的完整路径：(推荐将数据集放在E:\Code\Set\Open\MathModelAgent\project\sample_data目录下)",
            default=r"E:\Code\Set\Open\MathModelAgent\project\sample_data",
            validate=lambda x: os.path.exists(x) and os.path.isdir(x),
            only_directories=True,
        ),
        bg_file_path=questionary.path(
            "请输入题目文件路径",
            default=r"E:\Code\Set\Open\MathModelAgent\project\example\2023华数杯C题\questions_test.txt",
            validate=lambda x: os.path.exists(x)
            and os.path.isfile(x)
            and x.endswith((".txt", ".md")),
        ),
    ).ask()

    with open(answers["bg_file_path"], "r", encoding="utf-8") as f:
        bg_ques_all = f.read()

    log.debug(f"用户输入: {answers}")

    choice: Template = answers["template"]
    format_out_put: FormatOutPut = answers["format_out_put"]
    data_folder_path: str = answers["data_folder_path"]
    bg_ques_all: str = bg_ques_all

    user_input = UserInput(
        choice=choice,
        format_out_put=format_out_put,
        data_folder_path=data_folder_path,
        bg_ques_all=bg_ques_all,
        model=model,
    )
    input_content.set_user_input(user_input)
    log.info(user_input)
    return user_input


def center_cli_str(text: str, width: int | None = None):
    import shutil

    width = width or shutil.get_terminal_size().columns
    lines = text.split("\n")
    max_line_len = max(len(line) for line in lines)
    return "\n".join(
        (line + " " * (max_line_len - len(line))).center(width) for line in lines
    )


def get_ascii_banner(center: bool = True) -> str:
    text = dedent(
        r"""
        ===============================================================================
         __  __       _   _     __  __           _      _                          _   
        |  \/  |     | | | |   |  \/  |         | |    | |   /\                   | |  
        | \  / | __ _| |_| |__ | \  / | ___   __| | ___| |  /  \   __ _  ___ _ __ | |_ 
        | |\/| |/ _` | __| '_ \| |\/| |/ _ \ / _` |/ _ \ | / /\ \ / _` |/ _ \ '_ \| __|
        | |  | | (_| | |_| | | | |  | | (_) | (_| |  __/ |/ ____ \ (_| |  __/ | | | |_ 
        |_|  |_|\__,_|\__|_| |_|_|  |_|\___/ \__,_|\___|_/_/    \_\__, |\___|_| |_|\__|
                                                                    __/ |               
                                                                |___/                
        ===============================================================================
        """,
    ).strip()
    if center:
        return center_cli_str(text)
    else:
        return text
