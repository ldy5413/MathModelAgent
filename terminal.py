from config.config import Config
from utils.cli import get_user_input_from_ternimal
from models.user_output import UserOutput
from core.LLM import DeepSeekModel
from utils.data_recorder import DataRecorder
from utils.logger import log
from utils.common_utils import create_work_directories, create_task_id, load_toml
from models.task import Task
from utils.cli import get_ascii_banner


def start():
    print(get_ascii_banner())
    # === 初始化 ===
    # 设置控制台日志级别为
    log.set_console_level("WARNING")
    # 初始化日志系统，设置日志目录
    task_id = create_task_id()
    base_dir, dirs = create_work_directories(task_id)
    log.init(dirs["log"])

    config = Config(load_toml("config/config.toml"))

    ####################################################

    data_recorder = DataRecorder(dirs["log"])

    deepseek_model = DeepSeekModel(
        **config.get_model_config(), data_recorder=data_recorder
    )

    # TODO:print some detail and config

    user_input = get_user_input_from_ternimal(deepseek_model)

    user_input.set_config_template(config.get_config_template(user_input.comp_template))

    task = Task(
        task_id=task_id,
        base_dir=base_dir,
        work_dirs=dirs,
        llm=deepseek_model,
        config=config,
    )

    user_output: UserOutput = task.run(user_input, data_recorder)

    user_output.save_result(ques_count=user_input.get_ques_count())


if __name__ == "__main__":
    start()
