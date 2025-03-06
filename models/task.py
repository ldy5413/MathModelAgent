from models.user_input import UserInput
from models.user_output import UserOutput
from core.Agents import CoderAgent
from core.WorkFlow import SolutionWorkFlow, WriteWorkFlow


class Task:
    def __init__(
        self, task_id: str, base_dir: str, work_dirs: dict, llm=None, config=None
    ):
        self.task_id: str = task_id
        self.base_dir = base_dir
        self.work_dirs = work_dirs
        self.llm = llm
        self.config = config

    def run(self, user_input: UserInput, data_recorder) -> UserOutput:
        user_output = UserOutput(self.work_dirs, data_recorder=data_recorder)

        coder_agent = CoderAgent(
            self.llm,
            self.work_dirs["jupyter"],
            max_chat_turns=self.config.get_max_chat_turns(),
            max_retries=self.config.get_max_retries(),
            user_output=user_output,
        )

        solution_workflow = SolutionWorkFlow(coder_agent, user_input, user_output)
        solution_workflow.execute()

        write_workflow = WriteWorkFlow(
            model=self.llm, user_input=user_input, user_output=user_output
        )
        write_workflow.execute()

        return user_output
