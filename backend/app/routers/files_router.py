from fastapi import APIRouter
from app.utils.common_utils import get_current_files, get_work_dir
import os
import subprocess
from icecream import ic
from fastapi import HTTPException
from datetime import datetime
from app.services.redis_manager import redis_manager
from pathlib import Path

router = APIRouter()


@router.get("/download_url")
async def get_download_url(task_id: str, filename: str):
    return {"download_url": f"http://localhost:8000/static/{task_id}/{filename}"}


@router.get("/download_all_url")
async def get_download_all_url(task_id: str):
    return {"download_url": f"http://localhost:8000/static/{task_id}/all.zip"}


@router.get("/files")
async def get_files(task_id: str):
    work_dir = get_work_dir(task_id)
    files = get_current_files(work_dir, "all")
    file_all = []

    for i in files:
        file_type = i.split(".")[-1]
        file_all.append({"filename": i, "file_type": file_type})

    return file_all


@router.get("/open_folder")
async def open_folder(task_id: str):
    ic(task_id)
    # 打开工作目录
    work_dir = get_work_dir(task_id)

    # 打开工作目录
    if os.name == "nt":
        subprocess.run(["explorer", work_dir])
    elif os.name == "posix":
        subprocess.run(["open", work_dir])
    else:
        raise HTTPException(status_code=500, detail=f"不支持的操作系统: {os.name}")

    return {"message": "打开工作目录成功", "work_dir": work_dir}


@router.get("/tasks")
async def list_tasks():
    """列出历史任务（按时间倒序）

    返回字段：
    - task_id: 任务ID（目录名）
    - created_at: 创建时间（从目录名或文件时间推断，ISO 字符串）
    - status: running/completed/pending
    - has_md: 是否存在 res.md
    - has_docx: 是否存在 res.docx
    """
    base_dir = os.path.join("project", "work_dir")
    if not os.path.isdir(base_dir):
        return []

    entries = []
    names = [n for n in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, n))]
    # 读取 redis 客户端一次，避免重复连接
    client = await redis_manager.get_client()

    for name in names:
        task_dir = os.path.join(base_dir, name)
        res_md = os.path.join(task_dir, "res.md")
        res_docx = os.path.join(task_dir, "res.docx")

        # 推断时间：优先从 task_id 前缀解析 YYYYMMDD-HHMMSS
        try:
            dt = datetime.strptime("".join(name.split("-")[:2]), "%Y%m%d%H%M%S")
            created_at = dt.isoformat()
        except Exception:
            # 回退到文件系统时间
            created_at = datetime.fromtimestamp(os.path.getmtime(task_dir)).isoformat()

        # 判断状态
        has_md = os.path.isfile(res_md)
        has_docx = os.path.isfile(res_docx)
        try:
            is_running = await client.exists(f"task_id:{name}")
        except Exception:
            is_running = 0
        status = "running" if is_running else ("completed" if has_md or has_docx else "pending")

        entries.append(
            {
                "task_id": name,
                "created_at": created_at,
                "status": status,
                "has_md": has_md,
                "has_docx": has_docx,
            }
        )

    # 按时间倒序
    entries.sort(key=lambda x: x["created_at"], reverse=True)
    return entries


@router.get("/task_messages")
async def get_task_messages(task_id: str):
    """读取历史任务消息（用于查看历史任务页）。

    来源：后端在运行期会把每条消息追加到 logs/messages/{task_id}.json
    此接口直接把该文件内容读取并返回；若不存在返回空列表。
    """
    path = Path("logs/messages") / f"{task_id}.json"
    if not path.exists():
        return []
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 基本校验：必须是数组
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        # 读取失败时返回空数组，避免前端崩溃
        return []
