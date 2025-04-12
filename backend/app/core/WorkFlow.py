from openai import base_url
from app.core.agents import WriterAgent, CoderAgent
from app.core.llm import LLM
from app.schemas.request import Problem
from app.utils.log_util import logger
from app.utils.common_utils import create_work_dir, simple_chat
from app.utils.enums import CompTemplate, FormatOutPut
from app.models.user_input import UserInput
from app.utils.RichPrinter import RichPrinter
from app.models.user_output import UserOutput
from app.config.setting import settings
from app.core.llm import DeepSeekModel
import json

class WorkFlow:
    def __init__(self):
        pass

    def execute(self) -> str:
        RichPrinter.workflow_start()
        RichPrinter.workflow_end()


class MathModelWorkFlow(WorkFlow):
    task_id : str # 
    work_dir : str # worklow work dir
    ques_count: int = 0  # 问题数量
    questions: dict[str, str | int] = {}  # 问题
    
    async def execute(self,problem:Problem):
        self.task_id = problem.task_id
        self.work_dir = create_work_dir(self.task_id)

        # default choose deepseek model
        deepseek_model = DeepSeekModel(
            api_key = settings.DEEPSEEK_API_KEY,
            model = settings.DEEPSEEK_MODEL,
            base_url = settings.DEEPSEEK_BASE_URL,
            task_id = self.task_id,
        )   


        user_output = UserOutput()

        coder_agent = CoderAgent(
            model=deepseek_model,
            self.dirs,
            max_chat_turns=settings.MAX_CHAT_TURNS,
            max_retries=settings.MAX_RETRIES,
            user_output=user_output,
            task_id=self.task_id,
        )


        ################################################ solution steps
        solution_steps = self.get_solution_flows()

        for key, value in solution_steps.items():
            coder_response = await coder_agent.run(
                prompt=value["coder_prompt"], subtask_title=key
            )

            # TODO: 是否可以不需要coder_response
            writer_prompt = self.get_writer_prompt(
                key, coder_response, self.coder_agent.code_interpreter
            )
            # TODO: 自定义 writer_agent mode llm
            writer_agent = WriterAgent(
                model=self.coder_agent.model,
                comp_template=self.user_input.get_comp_template(),
                format_output=self.user_input.get_format_output(),
                user_output=self.user_output,
            )
            writer_response = writer_agent.run(
                writer_prompt,
                available_images=self.coder_agent.code_interpreter.get_created_images(
                    key
                ),
            )
            self.user_output.set_res(key, writer_response)
        # 关闭沙盒
        self.coder_agent.code_interpreter.shotdown_sandbox()
        logger.info(self.user_output.get_res())      

        ################################################ write steps


        write_workflow = WriteWorkFlow(
            model=self.llm, user_input=user_input, user_output=user_output
        )
        write_workflow.execute()

        user_output: UserOutput = await task.run(
                user_input, data_recorder=data_recorder
            )

            user_output.save_result(ques_count=user_input.get_ques_count())


        pass


   
        def format_questions(self,ques_all:str, model:LLM) -> None:
        """用户输入问题 使用LLM 格式化 questions"""
        # TODO:  "note": <补充说明,如果没有补充说明，请填 null>,
        from app.core.prompts import FORMAT_QUESTIONS_PROMPT
        history = [
            {
                "role": "system",
                "content":FORMAT_QUESTIONS_PROMPT,
            },
            {"role": "user", "content": ques_all},
        ]
        json_str = simple_chat(model, history)
        json_str = json_str.replace("```json", "").replace("```", "").strip()

        if not json_str:
            raise ValueError("返回的 JSON 字符串为空，请检查输入内容。")

        try:
            self.questions = json.loads(json_str)
            self.ques_count = self.questions["ques_count"]
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析错误: {e}")

        def get_solution_steps(self):
            questions_quesx = {
            key: value
            for key, value in self.questions.items()
            if key.startswith("ques") and key != "ques_count"
        }
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
                "coder_prompt": """
                        对当前目录下数据进行EDA分析(数据清洗,可视化),清洗后的数据保存当前目录下,**不需要复杂的模型**
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
          self, key: str, coder_response: str, code_interpreter: E2BCodeInterpreter
        ) -> str:
            """根据不同的key生成对应的writer_prompt

            Args:
                key: 任务类型
                coder_response: 代码执行结果

            Returns:
                str: 生成的writer_prompt
            """
            code_output = code_interpreter.get_code_output(key)

            # TODO: 结果{coder_response} 是否需要
            # TODO: 将当前产生的文件，路径发送给 writer_agent
            questions_quesx_keys = self.get_questions_quesx_keys()
            # TODO： 小标题编号
            # 题号最多6题
            bgc = self.get_questions()["background"]
            quesx_writer_prompt = {
                key: f"""
                    问题背景{bgc},不需要编写代码,代码手得到的结果{coder_response},{code_output},按照如下模板撰写：{self.config_template[key]}
                """
                for key in questions_quesx_keys
            }

            writer_prompt = {
                "eda": f"""
                    问题背景{bgc},不需要编写代码,代码手得到的结果{coder_response},{code_output},按照如下模板撰写：{self.config_template["eda"]}
                """,
                **quesx_writer_prompt,
                "sensitivity_analysis": f"""
                    问题背景{bgc},不需要编写代码,代码手得到的结果{coder_response},{code_output},按照如下模板撰写：{self.config_template["sensitivity_analysis"]}
                """,
            }

            if key in writer_prompt:
                return writer_prompt[key]
            else:
                raise ValueError(f"未知的任务类型: {key}")


class SolutionWorkFlow(WorkFlow):
    def __init__(
        self, coder_agent: CoderAgent, user_input: UserInput, user_output: UserOutput
    ):
        super().__init__(user_input, user_output)
        self.coder_agent = coder_agent

    async def execute(self) -> dict:
        RichPrinter.workflow_start()

        RichPrinter.workflow_end()
        return self.user_output.get_res()


# Parallel : 并行完成
class WriteWorkFlow(WorkFlow):
    def __init__(self, model: LLM, user_input: UserInput, user_output: UserOutput):
        super().__init__(user_input, user_output)
        self.model = model

    def execute(self) -> str:
        RichPrinter.workflow_start()
        flows = self.user_input.get_write_flows(self.user_output)
        for key, value in flows.items():
            # TODO: writer_agent 是否不需要初始化
            writer_agent = WriterAgent(
                model=self.model,
                comp_template=self.user_input.get_comp_template(),
                format_output=self.user_input.get_format_output(),
                user_output=self.user_output,
            )
            writer_response = writer_agent.run(value)
            self.user_output.set_res(key, writer_response)
        logger.info(self.user_output.get_res())
        RichPrinter.workflow_end()
        return self.user_output.get_res()
