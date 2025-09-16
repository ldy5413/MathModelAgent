from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from app.core.workflow import MathModelWorkFlow
from app.schemas.enums import CompTemplate, FormatOutPut
from app.utils.log_util import logger
from app.services.redis_manager import redis_manager
from app.schemas.request import Problem
from app.schemas.response import SystemMessage
from app.utils.common_utils import (
    create_task_id,
    create_work_dir,
    get_current_files,
    md_2_docx,
)
import os
import asyncio
from fastapi import HTTPException
from icecream import ic
from app.schemas.request import ExampleRequest
from pydantic import BaseModel
import litellm
from app.config.setting import settings
import requests
from app.services.task_control import TaskControl
from app.services.task_registry import task_registry
import json as pyjson
import shutil
from typing import Literal, Optional

router = APIRouter()


class ValidateApiKeyRequest(BaseModel):
    api_key: str
    base_url: str
    model_id: str


class ValidateOpenalexEmailRequest(BaseModel):
    email: str


class ValidateOpenalexEmailResponse(BaseModel):
    valid: bool
    message: str


class ValidateApiKeyResponse(BaseModel):
    valid: bool
    message: str


class SaveApiConfigRequest(BaseModel):
    coordinator: dict
    modeler: dict
    coder: dict
    writer: dict
    openalex_email: str


class CheckpointRespondRequest(BaseModel):
    checkpoint_id: str
    # feedback_open: 用户点击“提供反馈”进入输入态；feedback: 提交反馈内容
    action: Literal["continue", "feedback", "feedback_open"]
    content: Optional[str] = None


@router.post("/save-api-config")
async def save_api_config(request: SaveApiConfigRequest):
    """
    保存验证成功的 API 配置到 settings
    """
    try:
        # 更新各个模块的设置
        if request.coordinator:
            settings.COORDINATOR_API_KEY = request.coordinator.get("apiKey", "")
            settings.COORDINATOR_MODEL = request.coordinator.get("modelId", "")
            settings.COORDINATOR_BASE_URL = request.coordinator.get("baseUrl", "")

        if request.modeler:
            settings.MODELER_API_KEY = request.modeler.get("apiKey", "")
            settings.MODELER_MODEL = request.modeler.get("modelId", "")
            settings.MODELER_BASE_URL = request.modeler.get("baseUrl", "")

        if request.coder:
            settings.CODER_API_KEY = request.coder.get("apiKey", "")
            settings.CODER_MODEL = request.coder.get("modelId", "")
            settings.CODER_BASE_URL = request.coder.get("baseUrl", "")

        if request.writer:
            settings.WRITER_API_KEY = request.writer.get("apiKey", "")
            settings.WRITER_MODEL = request.writer.get("modelId", "")
            settings.WRITER_BASE_URL = request.writer.get("baseUrl", "")

        if request.openalex_email:
            settings.OPENALEX_EMAIL = request.openalex_email

        return {"success": True, "message": "配置保存成功"}
    except Exception as e:
        logger.error(f"保存配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


@router.post("/validate-api-key", response_model=ValidateApiKeyResponse)
async def validate_api_key(request: ValidateApiKeyRequest):
    """
    验证 API Key 的有效性
    """
    try:
        # 兼容厂商差异：自动丢弃不被该厂商接受的 OpenAI 风格参数
        try:
            litellm.drop_params = True
        except Exception:
            pass
        # 使用 litellm 发送测试请求
        kwargs = {
            "api_key": request.api_key,
            "messages": [{"role": "user", "content": "hi"}],
            "model": request.model_id,
        }
        if request.base_url and request.base_url != "https://api.openai.com/v1":
            kwargs["base_url"] = request.base_url
        # logger.info(f"Validating API Key with params: {kwargs}")
        await litellm.acompletion(**kwargs)

        return ValidateApiKeyResponse(valid=True, message="✓ 模型 API 验证成功")
    except Exception as e:
        error_msg = str(e)

        # 解析不同类型的错误
        if "401" in error_msg or "Unauthorized" in error_msg:
            return ValidateApiKeyResponse(valid=False, message="✗ API Key 无效或已过期")
        elif "404" in error_msg or "Not Found" in error_msg:
            return ValidateApiKeyResponse(
                valid=False, message="✗ 模型 ID 不存在或 Base URL 错误"
            )
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            return ValidateApiKeyResponse(
                valid=False, message="✗ 请求过于频繁，请稍后再试"
            )
        elif "403" in error_msg or "Forbidden" in error_msg:
            return ValidateApiKeyResponse(
                valid=False, message="✗ API 权限不足或账户余额不足"
            )
        else:
            return ValidateApiKeyResponse(
                valid=False, message=f"✗ 验证失败: {error_msg}"
            )


@router.post("/validate-openalex-email", response_model=ValidateOpenalexEmailResponse)
async def validate_openalex_email(request: ValidateOpenalexEmailRequest):
    """
    验证 OpenAlex Email 的有效性
    """
    try:
        response = requests.get(
            f"https://api.openalex.org/works?mailto={request.email}"
        )
        logger.debug(f"OpenAlex Email 验证响应: {response}")
        response.raise_for_status()
        return ValidateOpenalexEmailResponse(
            valid=True, message="✓ OpenAlex Email 验证成功"
        )
    except Exception as e:
        return ValidateOpenalexEmailResponse(
            valid=False, message=f"✗ OpenAlex Email 验证失败: {str(e)}"
        )


@router.post("/example")
async def exampleModeling(
    example_request: ExampleRequest,
    background_tasks: BackgroundTasks,
):
    task_id = create_task_id()
    work_dir = create_work_dir(task_id)
    example_dir = os.path.join("app", "example", "example", example_request.source)
    ic(example_dir)
    with open(os.path.join(example_dir, "questions.txt"), "r", encoding="utf-8") as f:
        ques_all = f.read()

    current_files = get_current_files(example_dir, "data")
    for file in current_files:
        src_file = os.path.join(example_dir, file)
        dst_file = os.path.join(work_dir, file)
        with open(src_file, "rb") as src, open(dst_file, "wb") as dst:
            dst.write(src.read())
    # 存储任务创建信息（不立即启动）
    await redis_manager.set(f"task_id:{task_id}", task_id)  # 允许 WS 连接
    payload = {
        "ques_all": ques_all,
        "comp_template": str(CompTemplate.CHINA.value if hasattr(CompTemplate.CHINA, 'value') else CompTemplate.CHINA),
        "format_output": str(FormatOutPut.Markdown.value if hasattr(FormatOutPut.Markdown, 'value') else FormatOutPut.Markdown),
        # 明确记录作为输入数据的文件名，便于重置时保留
        "data_files": list(current_files),
    }
    client = await redis_manager.get_client()
    await client.set(f"task:{task_id}:payload", pyjson.dumps(payload))
    await client.set(f"task:{task_id}:status", "created")
    # 将 payload 也写入到工作目录，便于重置后仍能查看问题
    try:
        with open(os.path.join(work_dir, "payload.json"), "w", encoding="utf-8") as f:
            f.write(pyjson.dumps(payload, ensure_ascii=False, indent=2))
    except Exception:
        pass
    await redis_manager.publish_message(task_id, SystemMessage(content="任务已创建，点击开始执行。"))
    return {"task_id": task_id, "status": "created"}


@router.post("/modeling")
async def modeling(
    background_tasks: BackgroundTasks,
    ques_all: str = Form(...),  # 从表单获取
    comp_template: CompTemplate = Form(...),  # 从表单获取
    format_output: FormatOutPut = Form(...),  # 从表单获取
    language: str | None = Form(None),  # 'zh' | 'en'
    files: list[UploadFile] = File(default=None),
):
    task_id = create_task_id()
    work_dir = create_work_dir(task_id)

    # 如果有上传文件，保存文件
    if files:
        logger.info(f"开始处理上传的文件，工作目录: {work_dir}")
        saved_files: list[str] = []
        for file in files:
            try:
                data_file_path = os.path.join(work_dir, file.filename)
                logger.info(f"保存文件: {file.filename} -> {data_file_path}")

                # 确保文件名不为空
                if not file.filename:
                    logger.warning("跳过空文件名")
                    continue

                content = await file.read()
                if not content:
                    logger.warning(f"文件 {file.filename} 内容为空")
                    continue

                with open(data_file_path, "wb") as f:
                    f.write(content)
                logger.info(f"成功保存文件: {data_file_path}")
                saved_files.append(file.filename)

            except Exception as e:
                logger.error(f"保存文件 {file.filename} 失败: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"保存文件 {file.filename} 失败: {str(e)}"
                )
    else:
        logger.warning("没有上传文件")

    # 存储任务创建信息（不立即启动）
    await redis_manager.set(f"task_id:{task_id}", task_id)  # 允许 WS 连接
    # 语言标准化（默认中文）
    lang = (language or settings.LANGUAGE or "zh").lower()
    lang = "en" if lang.startswith("en") else "zh"

    payload = {
        "ques_all": ques_all,
        "comp_template": str(comp_template.value if hasattr(comp_template, 'value') else comp_template),
        "format_output": str(format_output.value if hasattr(format_output, 'value') else format_output),
        "data_files": saved_files if files else [],
        "language": lang,
    }
    client = await redis_manager.get_client()
    await client.set(f"task:{task_id}:payload", pyjson.dumps(payload))
    await client.set(f"task:{task_id}:status", "created")
    # 将 payload 也写入到工作目录，便于重置后仍能查看问题
    try:
        with open(os.path.join(work_dir, "payload.json"), "w", encoding="utf-8") as f:
            f.write(pyjson.dumps(payload, ensure_ascii=False, indent=2))
    except Exception:
        pass
    await redis_manager.publish_message(task_id, SystemMessage(content="任务已创建，点击开始执行。"))
    return {"task_id": task_id, "status": "created"}


async def run_modeling_task_async(
    task_id: str,
    ques_all: str,
    comp_template: CompTemplate,
    format_output: FormatOutPut,
    language: str = "zh",
):
    logger.info(f"run modeling task for task_id: {task_id}")

    # 在任务开始前自动校验四个 Agent 的模型配置
    async def _validate_single(name: str, api_key: str | None, model_id: str | None, base_url: str | None) -> str | None:
        if not model_id or model_id.strip() == "":
            return f"{name}: 模型未配置"
        try:
            kwargs = {
                "api_key": api_key,
                "messages": [{"role": "user", "content": "hi"}],
                "model": model_id,
            }
            if base_url and base_url != "https://api.openai.com/v1":
                kwargs["base_url"] = base_url
            logger.info(f"{name} 验证参数: {kwargs}")
            await litellm.acompletion(**kwargs)
            return None
        except Exception as e:
            return f"{name}: 验证失败 - {str(e)[:200]}"

    async def _validate_all() -> list[str]:
        tasks = [
            _validate_single("Coordinator", settings.COORDINATOR_API_KEY, settings.COORDINATOR_MODEL, settings.COORDINATOR_BASE_URL),
            _validate_single("Modeler", settings.MODELER_API_KEY, settings.MODELER_MODEL, settings.MODELER_BASE_URL),
            _validate_single("Coder", settings.CODER_API_KEY, settings.CODER_MODEL, settings.CODER_BASE_URL),
            _validate_single("Writer", settings.WRITER_API_KEY, settings.WRITER_MODEL, settings.WRITER_BASE_URL),
        ]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r]

    # 发送任务开始状态
    await redis_manager.publish_message(
        task_id,
        SystemMessage(content="任务开始处理"),
    )

    # 给一个短暂的延迟，确保 WebSocket 有机会连接
    await asyncio.sleep(1)

    # 执行验证
    validation_errors = await _validate_all()
    if validation_errors:
        msg = "\n".join(validation_errors)
        await redis_manager.publish_message(
            task_id,
            SystemMessage(content=f"模型配置验证失败:\n{msg}", type="error"),
        )
        logger.error(f"模型配置验证失败: {msg}")
        return
    else:
        await redis_manager.publish_message(
            task_id,
            SystemMessage(content="模型配置验证成功"),
        )

    problem = Problem(
        task_id=task_id,
        ques_all=ques_all,
        comp_template=comp_template,
        format_output=format_output,
        language=language,
    )

    # 创建任务并等待它完成
    task = asyncio.create_task(MathModelWorkFlow().execute(problem))
    # 设置超时时间（比如 300 分钟）
    await asyncio.wait_for(task, timeout=3600 * 5)

    # 发送任务完成状态
    await redis_manager.publish_message(
        task_id,
        SystemMessage(content="任务处理完成", type="success"),
    )
    # 转换md为docx
    md_2_docx(task_id)


@router.post("/task/pause")
async def pause_task(task_id: str):
    await TaskControl.pause(task_id)
    return {"success": True, "message": "任务已暂停"}


@router.post("/task/resume")
async def resume_task(task_id: str):
    await TaskControl.resume(task_id)
    return {"success": True, "message": "任务已继续"}


@router.get("/task/status")
async def task_status(task_id: str):
    paused = await TaskControl.is_paused(task_id)
    client = await redis_manager.get_client()
    status = await client.get(f"task:{task_id}:status")
    # 兼容旧逻辑：若注册表有运行任务或 status==running 则 running
    running = task_registry.is_running(task_id) or status == "running"
    return {"task_id": task_id, "paused": paused, "running": running, "status": status}


@router.post("/task/start")
async def task_start(task_id: str):
    client = await redis_manager.get_client()
    payload_raw = await client.get(f"task:{task_id}:payload")
    if not payload_raw:
        raise HTTPException(status_code=404, detail="任务不存在或缺少payload")
    payload = pyjson.loads(payload_raw)

    if task_registry.is_running(task_id):
        return {"success": False, "message": "任务已在运行"}

    # 启动前确保取消暂停标记
    try:
        await TaskControl.resume(task_id)
    except Exception:
        pass

    await client.set(f"task:{task_id}:status", "running")
    await redis_manager.publish_message(task_id, SystemMessage(content="任务开始执行"))

    async def runner():
        try:
            # 还原 Problem
            comp_template = CompTemplate.CHINA
            try:
                comp_template = CompTemplate[payload["comp_template"]] if isinstance(payload["comp_template"], str) else CompTemplate.CHINA
            except Exception:
                pass
            format_output = FormatOutPut.Markdown
            try:
                format_output = FormatOutPut[payload["format_output"]] if isinstance(payload["format_output"], str) else FormatOutPut.Markdown
            except Exception:
                pass
            # 语言
            language = "zh"
            try:
                language = str(payload.get("language", "zh")).lower()
                language = "en" if language.startswith("en") else "zh"
            except Exception:
                language = "zh"

            problem = Problem(
                task_id=task_id,
                ques_all=payload["ques_all"],
                comp_template=comp_template,
                format_output=format_output,
                language=language,
            )

            # 执行原有流程（不经 BackgroundTasks，便于取消）
            # 校验
            async def _validate_single(name: str, api_key: str | None, model_id: str | None, base_url: str | None) -> str | None:
                if not model_id or model_id.strip() == "":
                    return f"{name}: 模型未配置"
                try:
                    kwargs = {
                        "api_key": api_key,
                        "messages": [{"role": "user", "content": "hi"}],
                        "model": model_id,
                    }
                    if base_url and base_url != "https://api.openai.com/v1":
                        kwargs["base_url"] = base_url
                    logger.info(f"{name} 验证参数: {kwargs}")
                    await litellm.acompletion(**kwargs)
                    return None
                except Exception as e:
                    return f"{name}: 验证失败 - {str(e)[:200]}"

            async def _validate_all() -> list[str]:
                tasks = [
                    _validate_single("Coordinator", settings.COORDINATOR_API_KEY, settings.COORDINATOR_MODEL, settings.COORDINATOR_BASE_URL),
                    _validate_single("Modeler", settings.MODELER_API_KEY, settings.MODELER_MODEL, settings.MODELER_BASE_URL),
                    _validate_single("Coder", settings.CODER_API_KEY, settings.CODER_MODEL, settings.CODER_BASE_URL),
                    _validate_single("Writer", settings.WRITER_API_KEY, settings.WRITER_MODEL, settings.WRITER_BASE_URL),
                ]
                results = await asyncio.gather(*tasks)
                return [r for r in results if r]

            await redis_manager.publish_message(task_id, SystemMessage(content="任务开始处理"))
            await asyncio.sleep(1)

            validation_errors = await _validate_all()
            if validation_errors:
                msg = "\n".join(validation_errors)
                await redis_manager.publish_message(task_id, SystemMessage(content=f"模型配置验证失败:\n{msg}", type="error"))
                await client.set(f"task:{task_id}:status", "failed")
                return
            else:
                await redis_manager.publish_message(task_id, SystemMessage(content="模型配置验证成功"))

            await MathModelWorkFlow().execute(problem)
            await redis_manager.publish_message(task_id, SystemMessage(content="任务处理完成", type="success"))
            md_2_docx(task_id)
            await client.set(f"task:{task_id}:status", "completed")
        except asyncio.CancelledError:
            await redis_manager.publish_message(task_id, SystemMessage(content="任务已停止", type="warning"))
            await client.set(f"task:{task_id}:status", "stopped")
            raise
        except Exception as e:
            await redis_manager.publish_message(task_id, SystemMessage(content=f"任务执行失败: {e}", type="error"))
            await client.set(f"task:{task_id}:status", "failed")
        finally:
            task_registry.remove(task_id)

    t = asyncio.create_task(runner())
    task_registry.add(task_id, t)
    return {"success": True, "message": "任务已开始"}


@router.post("/task/checkpoint/respond")
async def checkpoint_respond(task_id: str, req: CheckpointRespondRequest):
    """处理前端的检查点响应（继续/反馈）。"""
    from app.services.checkpoint_control import CHECKPOINT_KEY_TPL, CHECKPOINT_HOLD_KEY_TPL
    client = await redis_manager.get_client()
    key = CHECKPOINT_KEY_TPL.format(task_id=task_id, checkpoint_id=req.checkpoint_id)
    hold_key = CHECKPOINT_HOLD_KEY_TPL.format(task_id=task_id, checkpoint_id=req.checkpoint_id)
    try:
        if req.action == "feedback_open":
            # 标记进入反馈输入态：后端暂停倒计时
            await client.set(hold_key, "1")
            await client.expire(hold_key, 3600)  # 最多保留 1h，避免无限挂起
        else:
            # 收到继续/反馈提交：写入响应并清理 hold
            payload = {"action": req.action, "content": req.content or ""}
            await client.set(key, pyjson.dumps(payload))
            await client.expire(key, 120)
            try:
                await client.delete(hold_key)
            except Exception:
                pass
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败: {e}")


@router.post("/task/stop")
async def task_stop(task_id: str):
    ok = task_registry.cancel(task_id)
    if not ok:
        return {"success": False, "message": "任务不在运行"}
    return {"success": True, "message": "停止信号已发送"}


@router.post("/task/reset")
async def task_reset(task_id: str, auto_start: bool = True):
    """重置任务：
    - 若在运行，先停止
    - 清空工作目录（project/work_dir/{task_id}）
    - 清除分段结果 res.partial.json/res.json/res.md/res.docx
    - 将状态置为 created
    - 可选：自动重新开始
    """
    # 停止运行中的任务
    task_registry.cancel(task_id)

    # 定向清理：根据 payload.json/redis 中记录的 data_files 保留输入文件，删除其余生成物
    from app.utils.common_utils import get_work_dir
    try:
        work_dir = get_work_dir(task_id)
    except Exception:
        work_dir = None

    if work_dir and os.path.isdir(work_dir):
        keep_files = {"payload.json", "input_payload.json"}
        # 从 Redis 或 payload.json 中读取 data_files
        data_files: list[str] = []
        try:
            payload_raw = await (await redis_manager.get_client()).get(f"task:{task_id}:payload")
            if payload_raw:
                pd = pyjson.loads(payload_raw)
                if isinstance(pd, dict) and isinstance(pd.get("data_files"), list):
                    data_files = [str(x) for x in pd["data_files"]]
        except Exception:
            pass
        if not data_files:
            try:
                pf = os.path.join(work_dir, "payload.json")
                if os.path.isfile(pf):
                    with open(pf, "r", encoding="utf-8") as f:
                        pd = pyjson.loads(f.read())
                    if isinstance(pd, dict) and isinstance(pd.get("data_files"), list):
                        data_files = [str(x) for x in pd["data_files"]]
            except Exception:
                pass
        # 归一化需要保留的绝对路径
        keep_abs = set()
        for n in data_files:
            abs_path = os.path.normpath(os.path.join(work_dir, n))
            keep_abs.add(abs_path)
        # payload 文件也保留
        keep_abs.add(os.path.normpath(os.path.join(work_dir, "payload.json")))
        keep_abs.add(os.path.normpath(os.path.join(work_dir, "input_payload.json")))
        try:
            # 自底向上遍历，删除非保留文件并清理空目录
            for root, dirs, files_in in os.walk(work_dir, topdown=False):
                for fn in files_in:
                    fp = os.path.normpath(os.path.join(root, fn))
                    if fp in keep_abs:
                        continue
                    # 不删除 all.zip 会导致旧包混淆 → 允许删除
                    try:
                        os.remove(fp)
                    except FileNotFoundError:
                        pass
                # 清理空目录（根目录除外）
                if root != work_dir:
                    try:
                        if not os.listdir(root):
                            shutil.rmtree(root, ignore_errors=True)
                    except Exception:
                        pass
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"清理生成文件失败: {e}")

    client = await redis_manager.get_client()
    await client.set(f"task:{task_id}:status", "created")
    await TaskControl.resume(task_id)  # 确保无暂停标记
    await redis_manager.publish_message(task_id, SystemMessage(content="任务已重置为初始状态"))

    if auto_start:
        return await task_start(task_id)
    return {"success": True, "message": "任务已重置"}
