from app.models.user_input import UserInput
from app.models.user_output import UserOutput
from app.core.Agents import CoderAgent
from app.core.WorkFlow import SolutionWorkFlow, WriteWorkFlow
from app.config.config import settings


class Task:
    def __init__(self, task_id: str, dirs: dict, llm=None):
        self.task_id: str = task_id
        self.dirs = dirs
        self.llm = llm

    def run(self, user_input: UserInput, data_recorder) -> UserOutput:
        user_output = UserOutput(self.dirs, data_recorder=data_recorder)

        coder_agent = CoderAgent(
            self.llm,
            self.dirs["jupyter"],
            max_chat_turns=settings.MAX_CHAT_TURNS,
            max_retries=settings.MAX_RETRIES,
            user_output=user_output,
            task_id=self.task_id,
        )

        solution_workflow = SolutionWorkFlow(coder_agent, user_input, user_output)
        solution_workflow.execute()

        write_workflow = WriteWorkFlow(
            model=self.llm, user_input=user_input, user_output=user_output
        )
        write_workflow.execute()

        return user_output
