import asyncio
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import redis
from pydantic_settings import BaseSettings
from celery import Celery
from app.schemas.request import Problem

app = FastAPI()


# 步骤 ①：读取命令行参数或默认环境
env = os.getenv("ENV", "dev")  # 默认 dev 模式

# 步骤 ②：加载对应的 .env 文件
load_dotenv(f".env.{env}")


# 步骤 ③：定义配置模型
class Settings(BaseSettings):
    environment: str = "dev"
    database_url: str
    debug: bool = False


settings = Settings()
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

# 配置 Celery
celery = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

UPLOAD_FOLDER = "./uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/config")
async def config():
    return {
        "environment": settings.environment,
        "database": settings.database_url,
        "debug": settings.debug,
    }


@app.post("/upload_files/")
async def upload_files(files: list[UploadFile] = File(...)):
    task_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_FOLDER, task_id)
    os.makedirs(file_path, exist_ok=True)
    for file in files:
        data_file_path = os.path.join(file_path, file.filename)
        with open(data_file_path, "wb") as f:
            f.write(file.file.read())
    redis_client.set(f"file:{task_id}", file_path)
    return {"task_id": task_id, "message": "Files uploaded successfully"}


@app.post("/modeling/")
async def modeling(problem: Problem):
    task_id = problem.task_id
    ques = problem.ques
    if task_id and redis_client.exists(f"file:{task_id}"):
        file_path = redis_client.get(f"file:{task_id}")
    else:
        task_id = str(uuid.uuid4())
        file_path = None  # 不依赖数据集

    # 发送任务到 celery
    celery_task = run_modeling_task.apply_async(args=[task_id, file_path, ques])

    return {"task_id": task_id, "status": "processing"}


@app.websocket("/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    print(f"WebSocket connected for task: {task_id}")
    await manager.connect(websocket)
    try:
        while True:
            status = redis_client.get(f"status:{task_id}")
            if status:
                print(f"Status: {status}")
                await manager.send_personal_message(f"You status: {status}", websocket)
            else:
                print("No status available")
                await manager.send_personal_message("No status available", websocket)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@celery.task
def run_modeling_task(task_id: str, file_path: str, ques: str):
    redis_client.set(f"status:{task_id}", "Starting modeling...")

    # 模拟计算
    import time

    time.sleep(20)  # 假设建模过程需要时间
    redis_client.set(f"status:{task_id}", "Modeling completed")

    return {"task_id": task_id, "result": "success"}
