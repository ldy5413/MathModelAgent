import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
import redis
import redis.asyncio as aioredis
from celery import Celery
import redis.client
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

# 配置 Redis
REDIS_URL = "redis://localhost:6379/0"
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
redis_async_client = aioredis.Redis.from_url(REDIS_URL)

# 配置 Celery
celery = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

PROJECT_FOLDER = "./projects"
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
async def modeling(problem: Problem):
    task_id = problem.task_id
    if task_id and redis_client.exists(f"task_id:{task_id}"):
        # 存在任务
        files_path = os.path.join(PROJECT_FOLDER, task_id)
    else:
        task_id = create_task_id()
        files_path = None  # 不依赖数据集

    # 发送任务到 celery
    celery_task = run_modeling_task.apply_async(args=[problem, files_path])

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
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True)
            if msg:
                try:
                    # 转换为AgentMessage确保格式正确
                    agent_msg = AgentMessage.model_validate_json(msg)
                    await manager.send_personal_message_json(
                        agent_msg.model_dump(), websocket
                    )
                except Exception as e:
                    print(f"Error parsing message: {e}")
                    await manager.send_personal_message(
                        "Error parsing message", websocket
                    )
            else:
                print("No status available")
                await manager.send_personal_message("No status available", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@celery.task
def run_modeling_task(problem: Problem, files_path: str):
    mathmodelagent = MathModelAgent(problem, files_path)
    mathmodelagent.start()
    return {"task_id": problem.task_id, "result": "success"}
