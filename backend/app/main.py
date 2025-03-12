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
from app.schemas.request import Problem
from app.schemas.response import AgentMessage
from app.utils.connection import manager
from app.config.config import settings
from app.utils.common_utils import create_task_id, create_work_directories
from app.mathmodelagent import MathModelAgent

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


@app.post("/upload_files/")
async def upload_files(files: list[UploadFile] = File(...)):
    task_id = create_task_id()
    base_dir, dirs = create_work_directories(task_id)
    for file in files:
        data_file_path = os.path.join(dirs["data"], file.filename)
        with open(data_file_path, "wb") as f:
            f.write(file.file.read())
    redis_client.set(f"task_id:{task_id}", task_id)
    return {"task_id": task_id, "message": "Files uploaded successfully"}


@app.post("/modeling/")
async def modeling(problem: Problem, background_tasks: BackgroundTasks):
    task_id = problem.task_id
    dirs = None
    if task_id and redis_client.exists(f"task_id:{task_id}"):
        # 存在任务，创建完整的目录结构
        base_dir, dirs = create_work_directories(task_id)
    # else:
    #     task_id = create_task_id()
    #     files_path = None  # 不依赖数据集

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
    print(f"Subscribed to Redis channel: task:{task_id}:messages")  # 确认订阅频道
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True)
            if msg:
                try:
                    # 转换为AgentMessage确保格式正确
                    agent_msg = AgentMessage.model_validate_json(msg["data"])
                    await manager.send_personal_message_json(
                        agent_msg.model_dump(), websocket
                    )
                except Exception as e:
                    print(f"Error parsing message: {e}")
                    await manager.send_personal_message(
                        "Error parsing message", websocket
                    )
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def run_modeling_task_async(problem: dict, dirs: dict):
    print("run_modeling_task_async")

    # 测试发送
    from app.utils.enums import AgentType

    agent_msg = AgentMessage(
        agent_type=AgentType.CODER,
        code="processing",
        content="processing",
    )

    await redis_async_client.publish(
        f"task:{problem['task_id']}:messages",
        agent_msg.model_dump_json(),
    )

    # 将问题字典转换为Problem对象
    problem = Problem(**problem)
    mathmodelagent = MathModelAgent(problem, dirs)

    mathmodelagent.start()
    return {"task_id": problem.task_id, "result": "success"}
