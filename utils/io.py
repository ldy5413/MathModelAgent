from cli import UserInput
from utils.data_recorder import DataRecorder
from utils.logger import log
from utils.common_utils import create_work_directories, create_task_id, load_toml
import os


class InputContent:
    """all input content"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.user_input: UserInput = None
            self.task_id: str = create_task_id()
            self.base_dir, self.work_dirs = create_work_directories(self.task_id)
            self.config = load_toml("config/config.toml")
            self.md_template = load_toml("config/md_template.toml")

    def set_user_input(self, user_input: UserInput):
        self.user_input = user_input

    def get_user_input(self):
        return self.user_input

    def get_work_dirs(self):
        if not self.work_dirs:
            raise ValueError("未知的工作目录")
        return self.work_dirs

    def get_config(self):
        return self.config

    def get_md_template(self):
        return self.md_template

    def get_data_path(self) -> list[str]:
        """获取数据集路径"""
        data_folder_path = self.user_input.get_data_folder_path()
        files = os.listdir(data_folder_path)
        full_paths = [os.path.join(data_folder_path, file) for file in files]
        return full_paths

    def get_solution_flows(self):
        questions_quesx = self.user_input.get_questions_quesx()

        ques_flow = {
            key: {
                "coder_prompt": f"""
                    完成如下问题{value}
                """,
            }
            for key, value in questions_quesx.items()
        }
        flows = {
            "eda": {
                # TODO ： 获取当前路径下的所有数据集
                "coder_prompt": f"""
                    对数据 {self.get_data_path()} 进行EDA分析(数据清洗,可视化),清洗后的数据保存当前目录下,**不需要复杂的模型**
                """,
            },
            **ques_flow,
            "sensitivity_analysis": {
                "coder_prompt": """
                    根据上面建立的模型，选择一个模型，完成敏感性分析
                """,
            },
        }

        return flows

    def get_writer_prompt(self, key: str, coder_response: str) -> str:
        """根据不同的key生成对应的writer_prompt

        Args:
            key: 任务类型
            coder_response: 代码执行结果

        Returns:
            str: 生成的writer_prompt
        """
        from utils.notebook_serializer import notebook_serializer

        notebook_output = notebook_serializer.get_notebook_output_content(key)
        # TODO: 结果{coder_response} 是否需要
        # TODO: 将当前产生的文件，路径发送给 writer_agent
        questions_quesx_keys = self.user_input.get_questions_quesx_keys()
        # TODO： 小标题编号
        # 题号最多6题
        quesx_writer_prompt = {
            key: f"""
                问题背景{self.user_input.get_questions()["background"]},不需要编写代码,代码手得到的结果{coder_response},{notebook_output},按照如下模板撰写：{self.md_template[key]}
            """
            for key in questions_quesx_keys
        }

        writer_prompt = {
            "eda": f"""
                问题背景{self.user_input.get_questions()["background"]},不需要编写代码,代码手得到的结果{coder_response},{notebook_output},按照如下模板撰写：{self.md_template["eda"]}
            """,
            **quesx_writer_prompt,
            "sensitivity_analysis": f"""
                问题背景{self.user_input.get_questions()["background"]},不需要编写代码,代码手得到的结果{coder_response},{notebook_output},按照如下模板撰写：{self.md_template["sensitivity_analysis"]}
            """,
        }

        if key in writer_prompt:
            return writer_prompt[key]
        else:
            raise ValueError(f"未知的任务类型: {key}")

    def get_write_flows(self):
        model_build_solve = output_content.get_model_build_solve()
        bg_ques_all = self.user_input.get_bg_ques_all()
        flows = {
            "firstPage": f"""问题背景{bg_ques_all},不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{self.md_template["firstPage"]}，撰写标题，摘要，关键词""",
            "RepeatQues": f"""问题背景{bg_ques_all},不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{self.md_template["RepeatQues"]}，撰写问题重述""",
            "analysisQues": f"""问题背景{bg_ques_all},不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{self.md_template["analysisQues"]}，撰写问题分析""",
            "modelAssumption": f"""问题背景{bg_ques_all},不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{self.md_template["modelAssumption"]}，撰写模型假设""",
            "symbol": f"""不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{self.md_template["symbol"]}，撰写符号说明部分""",
            "judge": f"""不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{self.md_template["judge"]}，撰写模型的评价部分""",
            # TODO: 修改参考文献插入方式
            "reference": f"""不需要编写代码,根据模型的求解的信息{model_build_solve}，可以生成参考文献,按照如下模板撰写：{self.md_template["reference"]}，撰写参考文献""",
        }
        return flows

    def get_work_dir(self, key: str) -> str:
        if key not in self.work_dirs:
            raise ValueError(f"未知的工作目录: {key}")
        return self.work_dirs[key]


class OutputContent:
    """all output content"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.res: dict[str, str] = {
                # "eda": "",
                # "ques1": "",
            }
            self.data_recorder = DataRecorder(
                log_work_dir=input_content.get_work_dir("log")
            )
            self.cost_time = 0.0
            self.initialized = True

    def set_res(self, key: str, value: str):
        self.res[key] = value  # TODO： 换种数据类型有顺序

    def get_res(self):
        return self.res

    def get_model_build_solve(self) -> str:
        """获取模型求解"""
        model_build_solve = ",".join(
            f"{key}-{value}"
            for key, value in self.res.items()
            if key.startswith("ques") and key != "ques_count"
        )

        return model_build_solve

    def print_summary(self):
        """打印统计摘要"""
        log.info("Token Usage Summary:")
        pass

    def get_result_to_save(self):
        # 动态顺序获取拼接res value，正确拼接顺序
        ques_str = [
            f"ques{i}" for i in range(1, input_content.user_input.get_ques_count() + 1)
        ]
        seq = [
            "firstPage",
            "RepeatQues",
            "analysisQues",
            "modelAssumption",
            "symbol",
            "eda",
            *ques_str,
            "sensitivity_analysis",
            "judge",
            "reference",
        ]
        return "\n".join([self.res[key] for key in seq])

    def save_result(self):
        res_path = os.path.join(input_content.work_dirs["res"], "res.md")
        with open(res_path, "w", encoding="utf-8") as f:
            f.write(self.get_result_to_save())
        log.info(f"结果已保存到 {res_path}")


# 创建全局单例实例
input_content = InputContent()
output_content = OutputContent()

# 导出实例
__all__ = ["input_content", "output_content"]
