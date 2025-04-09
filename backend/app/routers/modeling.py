from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from app.config.setting import settings
from app.utils.redis_client import redis_async_client
from app.schemas.request import Problem
from app.schemas.response import AgentMessage, AgentType
from app.mathmodelagent import MathModelAgent
from app.utils.common_utils import create_task_id, create_work_directories
import os
import asyncio

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/config")
async def config():
    return {
        "environment": settings.ENV,
        "deepseek_model": settings.DEEPSEEK_MODEL,
        "deepseek_base_url": settings.DEEPSEEK_BASE_URL,
        "max_chat_turns": settings.MAX_CHAT_TURNS,
        "max_retries": settings.MAX_RETRIES,
        "CORS_ALLOW_ORIGINS": settings.CORS_ALLOW_ORIGINS,
    }


@router.post("/modeling/")
async def modeling(
    background_tasks: BackgroundTasks,
    ques_all: str = Form(...),  # 从表单获取
    comp_template: str = Form(...),  # 从表单获取
    format_output: str = Form(...),  # 从表单获取
    files: list[UploadFile] = File(default=None),
):
    task_id = create_task_id()
    _, dirs = create_work_directories(task_id)

    # 如果有上传文件，保存文件
    if files:
        for file in files:
            data_file_path = os.path.join(dirs["data"], file.filename)
            with open(data_file_path, "wb") as f:
                f.write(file.file.read())

    # 存储任务ID
    redis_async_client.set(f"task_id:{task_id}", task_id)

    # 创建 Problem 对象
    problem = Problem(
        task_id=task_id,
        ques_all=ques_all,
        comp_template=comp_template,
        format_output=format_output,
    )
    print(f"Adding background task for task_id: {task_id}")
    # 将任务添加到后台执行
    background_tasks.add_task(run_modeling_task_async, problem.model_dump(), dirs)
    return {"task_id": task_id, "status": "processing"}


async def run_modeling_task_async(problem: dict, dirs: dict):
    print("run_modeling_task_async")
    try:
        problem = Problem(**problem)
        mathmodel_agent = MathModelAgent(problem, dirs)

        # 发送任务开始状态
        await redis_async_client.publish(
            f"task:{problem.task_id}:messages",
            AgentMessage(
                agent_type=AgentType.SYSTEM, content="任务开始处理"
            ).model_dump_json(),
        )

        # 给一个短暂的延迟，确保 WebSocket 有机会连接
        await asyncio.sleep(1)

        # 创建任务并等待它完成
        try:
            task = asyncio.create_task(mathmodel_agent.start())
            # 设置超时时间（比如 30 分钟）
            await asyncio.wait_for(task, timeout=1800)
        except asyncio.TimeoutError:
            print(f"Task {problem.task_id} timed out")
            await redis_async_client.publish(
                f"task:{problem.task_id}:messages",
                AgentMessage(
                    agent_type=AgentType.SYSTEM, content="任务执行超时"
                ).model_dump_json(),
            )
        except Exception as e:
            print(f"Error in task execution: {str(e)}")
            await redis_async_client.publish(
                f"task:{problem.task_id}:messages",
                AgentMessage(
                    agent_type=AgentType.SYSTEM, content=f"任务执行错误: {str(e)}"
                ).model_dump_json(),
            )

        # 发送任务完成状态
        await redis_async_client.publish(
            f"task:{problem.task_id}:messages",
            AgentMessage(
                agent_type=AgentType.SYSTEM, content="任务处理完成"
            ).model_dump_json(),
        )

        return {"task_id": problem.task_id, "result": "success"}
    except Exception as e:
        print(f"Error in run_modeling_task_async: {str(e)}")
        # 发送错误状态
        await redis_async_client.publish(
            f"task:{problem.task_id}:messages",
            AgentMessage(
                agent_type=AgentType.SYSTEM, content=f"任务处理出错: {str(e)}"
            ).model_dump_json(),
        )
        raise
