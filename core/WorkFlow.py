from core.Agents import WriterAgent, CoderAgent
from core.LLM import BaseModel
from utils.logger import log
from utils.io import input_content, output_content
from utils.RichPrinter import RichPrinter


class WorkFlow:
    def __init__(self):
        pass

    def execute(self) -> str:
        RichPrinter.workflow_start()
        RichPrinter.workflow_end()


class SolutionWorkFlow(WorkFlow):
    def __init__(self, coder_agent: CoderAgent):
        self.coder_agent = coder_agent
        self.create_images: list[str] = []
        self.current_images: list[str] = []

    def execute(self) -> dict:
        RichPrinter.workflow_start()
        flows = input_content.get_solution_flows()

        for key, value in flows.items():
            coder_response = self.coder_agent.run(
                value["coder_prompt"], subtask_title=key
            )

            # TODO: 是否可以不需要coder_response
            writer_prompt = input_content.get_writer_prompt(key, coder_response)
            writer_agent = WriterAgent(
                model=self.coder_agent.model,
            )
            writer_response = writer_agent.run(
                writer_prompt, available_images=self.coder_agent.get_created_images()
            )
            output_content.set_res(key, writer_response)
        log.info(output_content.get_res())
        RichPrinter.workflow_end()
        return output_content.get_res()


# Parallel : 并行完成
class WriteWorkFlow(WorkFlow):
    def __init__(self, model: BaseModel):
        self.model = model

    def execute(self) -> str:
        RichPrinter.workflow_start()
        flows = input_content.get_write_flows()
        for key, value in flows.items():
            # TODO: writer_agent 是否不需要初始化
            writer_agent = WriterAgent(model=self.model)
            writer_response = writer_agent.run(value)
            output_content.set_res(key, writer_response)
        log.info(output_content.get_res())
        RichPrinter.workflow_end()
        return output_content.get_res()
