import gradio as gr
from config.config import Config
from utils.common_utils import create_work_directories, create_task_id, load_toml
from utils.logger import log
from utils.cli import get_ascii_banner
from utils.data_recorder import DataRecorder
from core.LLM import DeepSeekModel
from models.user_input import UserInput
from models.task import Task
from models.user_output import UserOutput
from gradio import ChatMessage


def bot(history: list, agent_name: str, message: str):
    """用于流式输出消息到chatbot"""
    # 创建新消息
    new_message = ChatMessage(
        role="assistant",
        content=message,
        metadata={"title": agent_name, "status": "done"},
    )
    history.append(new_message)
    return history


def task_start(template, output_format, dataset_path, question, history):
    print(get_ascii_banner())
    # === 初始化 ===
    history = []  # 重置历史记录

    # 创建消息回调函数
    def message_callback(agent_name, message):
        nonlocal history
        history = bot(history, agent_name, message)
        return history

    try:
        # 初始化日志和基本设置
        log.set_console_level("WARNING")
        task_id = create_task_id()
        base_dir, dirs = create_work_directories(task_id)
        try:
            log.init(dirs["log"])
        except ValueError:
            pass

        # 添加初始状态消息
        history = bot(history, "系统", f"开始任务，ID: {task_id}")

        config = Config(load_toml("config/config.toml"))
        data_recorder = DataRecorder(dirs["log"])

        # 初始化模型
        deepseek_model = DeepSeekModel(
            **config.get_model_config(),
            data_recorder=data_recorder,
            message_callback=message_callback,
        )

        # 创建用户输入
        user_input = UserInput(
            comp_template=template,
            format_output=output_format,
            data_folder_path=dataset_path,
            bg_ques_all=question,
            model=deepseek_model,
        )

        user_input.set_config_template(
            config.get_config_template(user_input.comp_template)
        )

        # 创建任务
        task = Task(
            task_id=task_id,
            base_dir=base_dir,
            work_dirs=dirs,
            llm=deepseek_model,
            config=config,
        )

        # 运行任务
        user_output: UserOutput = task.run(user_input, data_recorder)
        user_output.save_result(ques_count=user_input.get_ques_count())

    except Exception as e:
        history = bot(history, "系统", f"错误: {str(e)}")

    return history


# 创建 Blocks 界面
with gr.Blocks() as demo:
    with gr.Row():
        # 左侧输入部分
        with gr.Column(scale=1):
            template = gr.Dropdown(
                ["国赛", "美赛"],
                label="模板",
                info="选择你需要的模板(目前只支持中文)",
                value="国赛",
            )
            output_format = gr.Dropdown(
                ["Markdown", "Latex"],
                label="输出格式",
                info="选择你需要的输出格式(目前只支持markdown)",
                value="Markdown",
            )
            dataset_path = gr.Textbox(
                label="输入数据集的相对文件夹路径：(推荐将数据集放在./project/sample_data 目录下)",
                value="./project/sample_data",
            )
            question = gr.Textbox(
                label="输入题目",
                value="",
            )
            submit_btn = gr.Button("提交")

        # 右侧聊天部分
        with gr.Column(scale=1):
            chatbot = gr.Chatbot(
                value=[],
                label="任务进度",
                type="messages",  # 指定使用 messages 类型
                height=500,
            )

    submit_btn.click(
        fn=task_start,
        inputs=[template, output_format, dataset_path, question, chatbot],
        outputs=chatbot,
        queue=True,
    )

demo.launch()
