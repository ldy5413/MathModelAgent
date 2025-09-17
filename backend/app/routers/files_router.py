from fastapi import APIRouter
from app.utils.common_utils import get_current_files, get_work_dir
import os
import subprocess
from icecream import ic
from fastapi import HTTPException
from datetime import datetime
from app.services.redis_manager import redis_manager
from pathlib import Path
import zipfile

router = APIRouter()


@router.get("/download_url")
async def get_download_url(task_id: str, filename: str):
    # 返回相对路径，前端用其 API 基础前缀（如 /api）拼接，
    # 以同时兼容本地开发代理和反向代理域名访问。
    return {"download_url": f"/static/{task_id}/{filename}"}


@router.get("/download_all_url")
async def get_download_all_url(task_id: str):
    # 打包工作目录下所有文件为 all.zip（排除 all.zip 自身）
    work_dir = get_work_dir(task_id)
    zip_path = os.path.join(work_dir, "all.zip")

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(work_dir):
                for fn in files:
                    if fn == "all.zip":
                        continue
                    abs_path = os.path.join(root, fn)
                    rel_path = os.path.relpath(abs_path, work_dir)
                    zf.write(abs_path, rel_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打包失败: {e}")

    # 返回相对路径，前端负责拼接基础前缀
    return {"download_url": f"/static/{task_id}/all.zip"}


@router.get("/files")
async def get_files(task_id: str):
    work_dir = get_work_dir(task_id)
    entries = []
    try:
        for name in os.listdir(work_dir):
            path = os.path.join(work_dir, name)
            if os.path.isfile(path):
                st = os.stat(path)
                entries.append(
                    {
                        "name": name,
                        "size": st.st_size,
                        "modified_time": datetime.fromtimestamp(st.st_mtime).isoformat(),
                        "type": name.split(".")[-1].lower() if "." in name else "file",
                    }
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {e}")
    entries.sort(key=lambda x: x["modified_time"], reverse=True)
    return entries


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
            status_val = await client.get(f"task:{name}:status")
        except Exception:
            status_val = None
        if not status_val:
            # 兼容旧逻辑
            try:
                is_running = await client.exists(f"task_id:{name}")
            except Exception:
                is_running = 0
            status_val = "running" if is_running else ("completed" if has_md or has_docx else "pending")
        # 规范化状态：未知状态一律视为 completed
        allowed = {"created", "running", "stopped", "completed", "failed", "pending"}
        if status_val not in allowed:
            status_val = "completed"

        entries.append(
            {
                "task_id": name,
                "created_at": created_at,
                "status": status_val,
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


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除历史任务及其相关资源。

    操作内容：
    - 若任务在运行，先尝试取消
    - 删除工作目录 `project/work_dir/{task_id}`
    - 删除消息日志 `logs/messages/{task_id}.json`
    - 清理与该任务相关的 Redis 键
    """
    from app.services.task_registry import task_registry
    from app.services.task_control import PAUSE_KEY_TPL

    # 1) 取消运行中的任务
    try:
        task_registry.cancel(task_id)
    except Exception:
        pass

    # 2) 删除工作目录
    try:
        work_dir = get_work_dir(task_id)
        if os.path.isdir(work_dir):
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除工作目录失败: {e}")

    # 3) 删除消息日志
    try:
        log_path = Path("logs/messages") / f"{task_id}.json"
        if log_path.exists():
            log_path.unlink(missing_ok=True)
    except Exception:
        pass

    # 4) 清理 Redis 键
    try:
        client = await redis_manager.get_client()
        keys = [
            f"task_id:{task_id}",
            f"task:{task_id}:payload",
            f"task:{task_id}:status",
            PAUSE_KEY_TPL.format(task_id=task_id),
        ]
        try:
            await client.delete(*keys)
        except TypeError:
            # 某些 redis 客户端不支持 *args
            for k in keys:
                try:
                    await client.delete(k)
                except Exception:
                    pass
    except Exception:
        pass

    return {"success": True, "message": "任务已删除"}
