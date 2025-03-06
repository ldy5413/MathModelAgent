from textwrap import dedent
import os
import questionary
from core.LLM import BaseModel
from utils.logger import log
from utils.enums import CompTemplate, FormatOutPut
from models.user_input import UserInput


def get_user_input_from_ternimal(model: BaseModel) -> UserInput:
    """获取用户输入"""
    # TODO: 完善：更美观style，错误处理validate，questionary.path
    answers = questionary.form(
        comp_template=questionary.select(
            "选择你需要的模板(目前只支持中文)",
            choices=[
                questionary.Choice(CompTemplate.value, value=CompTemplate)
                for CompTemplate in CompTemplate
            ],
            default=CompTemplate.CHINA,
        ),
        format_output=questionary.select(
            "选择你需要的输出格式(目前只支持markdown)",
            choices=[
                questionary.Choice(format_op.value, value=format_op)
                for format_op in FormatOutPut
            ],
            default=FormatOutPut.Markdown,
        ),
        # TODO: 完善验证：数据集路径
        data_folder_path=questionary.path(
            f"输入数据集的相对文件夹路径：(推荐将数据集放在{os.path.join('.', 'project', 'sample_data')} 目录下)",
            default=os.path.join(".", "project", "sample_data"),
            only_directories=True,
        ),
        bg_file_path=questionary.path(
            "请输入题目相对文件夹路径",
            default=os.path.join(
                ".", "project", "example", "2023华数杯C题", "questions_test.txt"
            ),
            # validate=lambda x: os.path.exists(x)
            # and os.path.isfile(x)
            # and x.endswith((".txt", ".md")),
        ),
    ).ask()

    with open(answers["bg_file_path"], "r", encoding="utf-8") as f:
        bg_ques_all = f.read()

    log.debug(f"用户输入: {answers}")

    comp_template: CompTemplate = answers["comp_template"]
    format_output: FormatOutPut = answers["format_output"]
    data_folder_path: str = answers["data_folder_path"]
    bg_ques_all: str = bg_ques_all

    user_input = UserInput(
        comp_template=comp_template,
        format_output=format_output,
        data_folder_path=data_folder_path,
        bg_ques_all=bg_ques_all,
        model=model,
    )
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
