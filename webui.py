import gradio as gr
import os
import threading
import time
from queue import Queue, Empty
from utils.enums import CompTemplate, FormatOutPut
from core.LLM import DeepSeekModel
from utils.data_recorder import DataRecorder
from utils.logger import log
from utils.common_utils import create_work_directories, create_task_id, load_toml
from config.config import Config
from models.task import Task
from models.user_input import UserInput

# 全局变量
message_queue = Queue()
is_processing = False
last_messages = {"CoderAgent": "", "WriterAgent": ""}
current_status = ""


def check_messages():
    """检查队列消息，更新状态。"""
    global current_status, last_messages

    while not message_queue.empty():
        msg = message_queue.get_nowait()
        agent, content, status = msg.get("agent"), msg.get("content"), msg.get("status")

        if status:
            current_status = status
        if content and agent in last_messages:
            last_messages[agent] = content

    return current_status, last_messages["CoderAgent"], last_messages["WriterAgent"]


def process_input(
    state,
    comp_template,
    format_output,
    data_folder_path,
    bg_text,
    progress=gr.Progress(),
):
    """处理用户输入并执行任务。"""
    global is_processing, current_status, last_messages

    is_processing = True
    current_status, last_messages = "初始化...", {"CoderAgent": "", "WriterAgent": ""}
    progress(0.1, desc="初始化中...")

    try:
        log.set_console_level("WARNING")
        task_id = create_task_id()
        base_dir, dirs = create_work_directories(task_id)
        log.init(dirs["log"])

        config = Config(load_toml("config/config.toml"))
        data_recorder = DataRecorder(dirs["log"])
        deepseek_model = DeepSeekModel(
            **config.get_model_config(),
            data_recorder=data_recorder,
            message_queue=message_queue,
        )

        user_input = UserInput(
            comp_template=CompTemplate[comp_template],
            format_output=FormatOutPut[format_output],
            data_folder_path=data_folder_path,
            bg_ques_all=bg_text,
            model=deepseek_model,
        )
        user_input.set_config_template(
            config.get_config_template(user_input.comp_template)
        )

        task = Task(task_id, base_dir, dirs, deepseek_model, config)
        user_output = task.run(user_input, data_recorder)
        user_output.save_result(ques_count=user_input.get_ques_count())

        is_processing = False
        return (
            state,
            f"✅ 任务完成！\n📌 任务ID: {task_id}\n📁 结果保存在: {base_dir}",
            *check_messages(),
        )
    except Exception as e:
        is_processing = False
        return state, f"❌ 发生错误: {str(e)}", *check_messages()


def periodic_update():
    """定期刷新状态。"""
    return check_messages()


# Gradio 界面
with gr.Blocks(title="数学建模助手", theme=gr.themes.Soft()) as demo:
    state = gr.State({"is_processing": False})

    gr.Markdown(
        """# 🎓 数学建模助手\n请按照步骤操作：选择竞赛模板、输出格式、数据路径，并输入题目内容。"""
    )

    with gr.Row():
        comp_template = gr.Dropdown(
            choices=[t.name for t in CompTemplate],
            value=CompTemplate.CHINA.name,
            label="竞赛模板",
        )
        format_output = gr.Dropdown(
            choices=[f.name for f in FormatOutPut],
            value=FormatOutPut.Markdown.name,
            label="输出格式",
        )
        data_folder = gr.Textbox(value="./project/sample_data", label="数据集路径")

    bg_text = gr.Textbox(lines=10, label="题目内容", placeholder="粘贴完整题目内容...")
    submit_btn = gr.Button("🚀 开始处理", variant="primary")
    output = gr.Textbox(label="处理进度", lines=10)
    agent_status, coder_output, writer_output = (
        gr.Textbox(label="Agent 状态"),
        gr.Markdown(label="Coder 输出"),
        gr.Markdown(label="Writer 输出"),
    )

    submit_btn.click(
        process_input,
        [state, comp_template, format_output, data_folder, bg_text],
        [state, output, agent_status, coder_output, writer_output],
    )
    gr.Button("刷新").click(
        periodic_update, [], [agent_status, coder_output, writer_output]
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1")
