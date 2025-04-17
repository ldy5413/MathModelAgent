from app.models.user_output import UserOutput
from app.tools.code_interpreter import E2BCodeInterpreter
from app.utils.enums import CompTemplate, FormatOutPut
from app.core.llm import LLM
from app.utils.common_utils import simple_chat
import json
import os


class UserInput:
    def __init__(
        self,
        comp_template: CompTemplate = CompTemplate.CHINA,
        format_output: FormatOutPut = FormatOutPut.Markdown,
        work_dir: str = "",
        ques_all: str = "",
        model: LLM = None,  # TODO: 不同任务选择不同模型
        init_with_llm: bool = True,  # 新增参数控制是否使用LLM初始化问题
    ):
        self.comp_template: CompTemplate = comp_template  # 选择模板
        self.format_output: FormatOutPut = format_output  # 选择输出格式
        self.work_dir: str = work_dir  # 数据文件夹路径
        self.ques_all: str = ques_all  # 用户输入的完整背景以及问题
        self.model: LLM = model  # 模型
        self.ques_count: int = 0  # 问题数量
        self.questions: dict[str, str | int] = {}  # 问题

        self.config_template = {}

    def set_questions_directly(self, questions: dict[str, str | int]) -> None:
        """直接设置questions,跳过LLM请求"""
        self.questions = questions
        self.ques_count = questions.get("ques_count", 0)

    def get_ques_count(self):
        return self.ques_count

    def get_comp_template(self):
        return self.comp_template

    def set_comp_template(self, comp_template):
        self.comp_template = comp_template

    def set_config_template(self, config_template):
        self.config_template = config_template

    def get_bg_ques_all(self):
        return self.bg_ques_all

    def get_format_output(self):
        return self.format_output

    def set_format_output(self, format_output):
        self.format_output = format_output

    def get_data_folder_path(self):
        return self.data_folder_path

    def set_data_folder_path(self, data_folder_path):
        self.data_folder_path = data_folder_path

    def get_questions(self):
        return self.questions

    def set_questions(self, questions):
        self.questions = questions

    def get_questions_quesx_keys(self) -> list[str]:
        """获取问题1,2...的键"""
        return list(self.get_questions_quesx().keys())

    def __str__(self):
        return f"choice: {self.comp_template}, format_out_put: {self.format_output}, data_folder_path: {self.data_folder_path}, bg_ques_all: {self.bg_ques_all}, model: {self.model}, ques_count: {self.ques_count}, questions: {self.questions}"

    def get_data_path(self) -> list[str]:
        data_folder_path = self.get_data_folder_path()  # "" ./project/sample_data
        files = os.listdir(data_folder_path)
        return files
