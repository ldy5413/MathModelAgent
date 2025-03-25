from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
import os
from app.utils.redis_client import redis_client, redis_async_client
from app.schemas.request import Problem, ProblemRequest
from app.schemas.response import AgentMessage
from app.utils.connection import manager
from app.config.config import settings
from app.utils.common_utils import create_task_id, create_work_directories
from app.mathmodelagent import MathModelAgent
from app.utils.enums import AgentType

app = FastAPI()
# origins = [
#     "http://localhost:3000",  # 前端开发服务器
#     "http://localhost:5173",  # Vite 开发服务器备选端口
#     "https://mathmode.zeabur.app",  # 生产环境
# ]
# 跨域 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PROJECT_FOLDER = "./project"
os.makedirs(PROJECT_FOLDER, exist_ok=True)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/config")
async def config():
    return {
        "environment": settings.ENV,
        "deepseek_model": settings.DEEPSEEK_MODEL,
        "deepseek_base_url": settings.DEEPSEEK_BASE_URL,
        "max_chat_turns": settings.MAX_CHAT_TURNS,
        "max_retries": settings.MAX_RETRIES,
    }


@app.post("/modeling/")
async def modeling(
    problem_request: ProblemRequest,
    background_tasks: BackgroundTasks,
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
    redis_client.set(f"task_id:{task_id}", task_id)

    # 将 ProblemRequest 转换为 Problem
    problem = Problem(
        task_id=task_id,
        ques_all=problem_request.ques_all,
        comp_template=problem_request.comp_template,
        format_output=problem_request.format_output,
    )
    print(problem)
    print(f"Adding background task for task_id: {task_id}")
    # 将任务添加到后台执行
    background_tasks.add_task(run_modeling_task_async, problem.model_dump(), dirs)
    return {"task_id": task_id, "status": "processing"}


@app.websocket("/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    if not redis_client.exists(f"task_id:{task_id}"):
        await websocket.close(code=1008, reason="Task not found")
        return
    print(f"WebSocket connected for task: {task_id}")

    await manager.connect(websocket)
    pubsub = redis_async_client.pubsub()

    # 订阅指定频道
    await pubsub.subscribe(f"task:{task_id}:messages")
    print(f"Subscribed to Redis channel: task:{task_id}:messages")

    try:
        import asyncio

        while True:
            try:
                # 创建两个并发任务：一个用于接收消息，一个用于发送心跳
                async def receive_messages():
                    while True:
                        msg = await pubsub.get_message(ignore_subscribe_messages=True)
                        if msg:
                            try:
                                agent_msg = AgentMessage.model_validate_json(
                                    msg["data"]
                                )
                                await websocket.send_json(agent_msg.model_dump())
                            except Exception as e:
                                print(f"Error parsing message: {e}")
                                await websocket.send_json({"error": str(e)})
                        await asyncio.sleep(0.1)  # 短暂休眠避免CPU过载

                async def send_heartbeat():
                    while True:
                        await websocket.send_json({"type": "heartbeat"})
                        await asyncio.sleep(1)  # 每秒发送一次心跳

                # 并发运行两个任务
                await asyncio.gather(
                    receive_messages(), send_heartbeat(), return_exceptions=True
                )

            except WebSocketDisconnect:
                print("WebSocket disconnected")
                break
            except Exception as e:
                print(f"Error in websocket loop: {e}")
                # 不立即退出，尝试继续运行
                await asyncio.sleep(1)
                continue

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await pubsub.unsubscribe(f"task:{task_id}:messages")
        manager.disconnect(websocket)
        print(f"WebSocket connection closed for task: {task_id}")


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

        await mathmodel_agent.start()

        # 发送任务完成状态
        await redis_async_client.publish(
            f"task:{problem.task_id}:messages",
            AgentMessage(
                agent_type=AgentType.SYSTEM, content="任务处理完成"
            ).model_dump_json(),
        )

        return {"task_id": problem.task_id, "result": "success"}
    except Exception as e:
        # 发送错误状态
        await redis_async_client.publish(
            f"task:{problem.task_id}:messages",
            AgentMessage(
                agent_type=AgentType.SYSTEM, content=f"任务处理出错: {str(e)}"
            ).model_dump_json(),
        )
        raise
