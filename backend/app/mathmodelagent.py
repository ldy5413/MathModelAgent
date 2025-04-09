from app.core.llm import DeepSeekModel
from app.utils.data_recorder import DataRecorder
from app.config.setting import settings
from app.models.task import Task
from app.models.user_output import UserOutput
from app.models.user_input import UserInput
from app.schemas.request import Problem
from app.utils.common_utils import get_config_template
from app.schemas.response import AgentMessage, AgentType
from app.utils.redis_client import redis_async_client


class MathModelAgent:
    def __init__(self, problem: Problem, dirs: dict):
        self.problem = problem
        self.dirs = dirs

    async def start(self):
        try:
            # 在关键步骤发送状态更新
            await redis_async_client.publish(
                f"task:{self.problem.task_id}:messages",
                AgentMessage(
                    agent_type=AgentType.SYSTEM, content="开始执行建模任务"
                ).model_dump_json(),
            )

            data_recorder = DataRecorder(self.dirs["log"])

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
                data_folder_path=self.dirs["data"],
                bg_ques_all=self.problem.ques_all,
                model=deepseek_model,
                init_with_llm=True,  # 使用LLM初始化
            )

            user_input.set_config_template(
                get_config_template(user_input.comp_template)
            )

            task = Task(
                task_id=self.problem.task_id,
                dirs=self.dirs,
                llm=deepseek_model,
            )

            user_output: UserOutput = await task.run(
                user_input, data_recorder=data_recorder
            )

            user_output.save_result(ques_count=user_input.get_ques_count())

            # 定期发送进度更新
            await redis_async_client.publish(
                f"task:{self.problem.task_id}:messages",
                AgentMessage(
                    agent_type=AgentType.SYSTEM, content="任务进行中..."
                ).model_dump_json(),
            )

        except Exception as e:
            print(f"Error in MathModelAgent.start: {str(e)}")
            await redis_async_client.publish(
                f"task:{self.problem.task_id}:messages",
                AgentMessage(
                    agent_type=AgentType.SYSTEM, content=f"建模过程出错: {str(e)}"
                ).model_dump_json(),
            )
            raise
