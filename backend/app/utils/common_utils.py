import os
import datetime
import hashlib
import tomllib
from app.core.llm import LLM
from app.utils.enums import CompTemplate
from app.utils.log_util import logger


def create_task_id() -> str:
    """生成任务ID"""
    # 生成时间戳和随机hash
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    random_hash = hashlib.md5(str(datetime.datetime.now()).encode()).hexdigest()[:8]
    return f"{timestamp}-{random_hash}"


def create_work_dir(task_id: str) -> str:
    # 设置主工作目录和子目录
    work_dir = os.path.join("project", "work_dir", task_id)

    # 检查目录是否已存在
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    else:
        print(f"目录已存在: {work_dir}")

    return work_dir


def get_work_dir(task_id: str) -> str:
    work_dir = os.path.join("project", "work_dir", task_id)
    if os.path.exists(work_dir):
        return work_dir
    else:
        logger.error(f"工作目录不存在: {work_dir}")
        raise FileNotFoundError(f"工作目录不存在: {work_dir}")


def get_config_template(comp_template: CompTemplate) -> dict:
    if comp_template == CompTemplate.CHINA:
        return load_toml(os.path.join("app", "config", "md_template.toml"))


def load_toml(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_markdown(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_current_files(folder_path: str, type: str = "all") -> list[str]:
    files = os.listdir(folder_path)
    if type == "all":
        return files

    elif type == "md":
        return [file for file in files if file.endswith(".md")]
    elif type == "ipynb":
        return [file for file in files if file.endswith(".ipynb")]
    elif type == "xlsx":
        return [file for file in files if file.endswith(".xlsx")]
    elif type == "image":
        return [
            file for file in files if file.endswith(".png") or file.endswith(".jpg")
        ]


def simple_chat(model: LLM, history: list) -> str:
    """
    Description of the function.

    Args:
        model (BaseModel): 模型
        history (list): 构造好的历史记录（包含system_prompt,user_prompt）

    Returns:
        return_type: Description of the return value.
    """
    kwargs = {
        "model": model.model,
        "messages": history,
        "stream": False,
    }

    completion = model.client.chat.completions.create(**kwargs)

    return completion.choices[0].message.content
