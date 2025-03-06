from core.Agents import WriterAgent, CoderAgent
from core.LLM import BaseModel
from models import user_output
from utils.logger import log
from models.user_input import UserInput
from models.user_output import UserOutput
from utils.RichPrinter import RichPrinter


class WorkFlow:
    def __init__(self, user_input: UserInput, user_output: UserOutput):
        self.user_input = user_input
        self.user_output = user_output

    def execute(self) -> str:
        RichPrinter.workflow_start()
        RichPrinter.workflow_end()


class SolutionWorkFlow(WorkFlow):
    def __init__(
        self, coder_agent: CoderAgent, user_input: UserInput, user_output: UserOutput
    ):
        super().__init__(user_input, user_output)
        self.coder_agent = coder_agent
        self.create_images: list[str] = []
        self.current_images: list[str] = []

    def execute(self) -> dict:
        RichPrinter.workflow_start()
        flows = self.user_input.get_solution_flows()

        for key, value in flows.items():
            coder_response = self.coder_agent.run(
                value["coder_prompt"], subtask_title=key
            )

            # TODO: 是否可以不需要coder_response
            writer_prompt = self.user_input.get_writer_prompt(
                key,
                coder_response,
                notebook_serializer=self.coder_agent.get_notebook_serializer(),
            )
            # TODO: 自定义 writer_agent mode llm
            writer_agent = WriterAgent(
                model=self.coder_agent.model,
                comp_template=self.user_input.get_comp_template(),
                format_output=self.user_input.get_format_output(),
                user_output=self.user_output,
            )
            writer_response = writer_agent.run(
                writer_prompt, available_images=self.coder_agent.get_created_images()
            )
            self.user_output.set_res(key, writer_response)
        log.info(self.user_output.get_res())
        RichPrinter.workflow_end()
        return self.user_output.get_res()


# Parallel : 并行完成
class WriteWorkFlow(WorkFlow):
    def __init__(
        self, model: BaseModel, user_input: UserInput, user_output: UserOutput
    ):
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
                user_output=self.user_output
                )
            writer_response = writer_agent.run(value)
            self.user_output.set_res(key, writer_response)
        log.info(self.user_output.get_res())
        RichPrinter.workflow_end()
        return self.user_output.get_res()
