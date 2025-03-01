from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings


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


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(
                f"You wrote: {data} {client_id}", websocket
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
