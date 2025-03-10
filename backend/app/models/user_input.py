from app.models.user_output import UserOutput
from app.utils.enums import CompTemplate, FormatOutPut
from app.core.LLM import LLM
from app.utils.logger import log
from app.utils.common_utils import simple_chat
import json
import os


class UserInput:
    def __init__(
        self,
        comp_template: CompTemplate = CompTemplate.CHINA,
        format_output: FormatOutPut = FormatOutPut.Markdown,
        data_folder_path: str = "",
        bg_ques_all: str = "",
        model: LLM = None,  # TODO: 不同任务选择不同模型
        init_with_llm: bool = True,  # 新增参数控制是否使用LLM初始化问题
    ):
        self.comp_template: CompTemplate = comp_template  # 选择模板
        self.format_output: FormatOutPut = format_output  # 选择输出格式
        self.data_folder_path: str = (
            data_folder_path  # 数据集存放的文件夹 .\project\sample_data
        )
        self.bg_ques_all: str = bg_ques_all  # 用户输入的完整背景以及问题
        self.model: LLM = model  # 模型
        self.ques_count: int = 0  # 问题数量
        self.questions: dict[str, str | int] = {}  # 问题

        self.config_template = {}

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
        return f"choice: {self.comp_template}, format_out_put: {self.format_output}, data_folder_path: {self.data_folder_path}, bg_ques_all: {self.bg_ques_all}, model: {self.model}, ques_count: {self.ques_count}, questions: {self.questions}"

    def get_data_path(self) -> list[str]:
        """获取数据集完整路径"""
        data_folder_path = self.get_data_folder_path() # "" ./project/sample_data
        files = os.listdir(data_folder_path)
        full_paths = [os.path.abspath(os.path.join(data_folder_path, file)) for file in files]
        log.info(f"full_paths: {full_paths}")
        return full_paths

    def get_solution_flows(self):
        questions_quesx = self.get_questions_quesx()

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

    def get_writer_prompt(
        self, key: str, coder_response: str, notebook_serializer
    ) -> str:
        """根据不同的key生成对应的writer_prompt

        Args:
            key: 任务类型
            coder_response: 代码执行结果

        Returns:
            str: 生成的writer_prompt
        """

        notebook_output = notebook_serializer.get_notebook_output_content(key)
        # TODO: 结果{coder_response} 是否需要
        # TODO: 将当前产生的文件，路径发送给 writer_agent
        questions_quesx_keys = self.get_questions_quesx_keys()
        # TODO： 小标题编号
        # 题号最多6题
        quesx_writer_prompt = {
            key: f"""
                问题背景{self.get_questions()["background"]},不需要编写代码,代码手得到的结果{coder_response},{notebook_output},按照如下模板撰写：{self.config_template[key]}
            """
            for key in questions_quesx_keys
        }

        writer_prompt = {
            "eda": f"""
                问题背景{self.get_questions()["background"]},不需要编写代码,代码手得到的结果{coder_response},{notebook_output},按照如下模板撰写：{self.config_template["eda"]}
            """,
            **quesx_writer_prompt,
            "sensitivity_analysis": f"""
                问题背景{self.get_questions()["background"]},不需要编写代码,代码手得到的结果{coder_response},{notebook_output},按照如下模板撰写：{self.config_template["sensitivity_analysis"]}
            """,
        }

        if key in writer_prompt:
            return writer_prompt[key]
        else:
            raise ValueError(f"未知的任务类型: {key}")

    def get_write_flows(self, user_output: UserOutput):
        model_build_solve = user_output.get_model_build_solve()
        bg_ques_all = self.get_bg_ques_all()
        flows = {
            "firstPage": f"""问题背景{bg_ques_all},不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{self.config_template["firstPage"]}，撰写标题，摘要，关键词""",
            "RepeatQues": f"""问题背景{bg_ques_all},不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{self.config_template["RepeatQues"]}，撰写问题重述""",
            "analysisQues": f"""问题背景{bg_ques_all},不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{self.config_template["analysisQues"]}，撰写问题分析""",
            "modelAssumption": f"""问题背景{bg_ques_all},不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{self.config_template["modelAssumption"]}，撰写模型假设""",
            "symbol": f"""不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{self.config_template["symbol"]}，撰写符号说明部分""",
            "judge": f"""不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{self.config_template["judge"]}，撰写模型的评价部分""",
            # TODO: 修改参考文献插入方式
            "reference": f"""不需要编写代码,根据模型的求解的信息{model_build_solve}，可以生成参考文献,按照如下模板撰写：{self.config_template["reference"]}，撰写参考文献""",
        }
        return flows
