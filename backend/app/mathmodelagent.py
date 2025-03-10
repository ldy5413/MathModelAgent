import os
from core.LLM import DeepSeekModel
from utils.data_recorder import DataRecorder
from utils.logger import log
from config.config import settings
from app.models.task import Task
from app.models.user_output import UserOutput
from app.models.user_input import UserInput
from app.schemas.request import Problem
from app.utils.common_utils import get_config_template


class MathModelAgent:
    def __init__(self, problem: Problem, files_path: str):
        self.problem = problem
        self.files_path = files_path

    def start(self):
        log.set_console_level("WARNING")
        log.init(self.files_path["log"])
        data_recorder = DataRecorder(self.files_path["log"])

        # 加载配置文件
        deepseek_model = DeepSeekModel(
            **settings.get_deepseek_config(),
            data_recorder=data_recorder,
            task_id=self.problem.task_id,
        )

        # 直接设置questions示例

        user_input = UserInput(
            comp_template=self.problem.comp_template,
            format_output=self.problem.format_output,
            data_folder_path=self.files_path["data"],
            bg_ques_all=self.problem.ques_all,
            model=deepseek_model,
            init_with_llm=True,  # 使用LLM初始化
        )

        user_input.set_config_template(get_config_template(user_input.comp_template))

        task = Task(
            task_id=self.problem.task_id,
            base_dir=self.files_path["base"],
            work_dirs=self.files_path["work"],
            llm=deepseek_model,
        )

        user_output: UserOutput = task.run(user_input, data_recorder=data_recorder)

        user_output.save_result(ques_count=user_input.get_ques_count())
