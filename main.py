from core.Agents import CoderAgent
from core.WorkFlow import SolutionWorkFlow, WriteWorkFlow
from cli import set_user_input_from_cli
from core.LLM import DeepSeekModel
from utils.logger import log
from utils.io import input_content, output_content


def init_task():
    # === 初始化 ===
    # 设置控制台日志级别为 DEBUG
    log.set_console_level("WARNING")
    # 初始化日志系统，设置日志目录
    log.init(input_content.work_dirs["log"])


def start():
    init_task()
    # 加载配置文件
    deepseek_model = DeepSeekModel(**input_content.get_config())

    # TODO:print some detail and config

    set_user_input_from_cli(deepseek_model)

    coder_agent = CoderAgent(
        deepseek_model, work_dir=input_content.work_dirs["jupyter"]
    )

    solution_workflow = SolutionWorkFlow(coder_agent)
    solution_workflow.execute()

    write_workflow = WriteWorkFlow(model=deepseek_model)
    write_workflow.execute()

    output_content.save_result()


if __name__ == "__main__":
    start()
