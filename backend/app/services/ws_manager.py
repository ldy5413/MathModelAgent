from fastapi import WebSocket
from starlette.websockets import WebSocketState
from app.utils.log_util import logger

class WebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def send_personal_message(self, message: str, websocket: WebSocket):
        if (
            websocket.client_state != WebSocketState.CONNECTED
            or websocket.application_state == WebSocketState.DISCONNECTED
        ):
            logger.warning("WebSocket not connected, cannot send message.")
            return
        try:
            await websocket.send_text(message)
        except Exception as e:
            # 连接已关闭或异常，忽略发送失败
            logger.error(f"Error sending message: {e}, ignoring.")
            pass

    async def send_personal_message_json(self, message: dict, websocket: WebSocket):
        if (
            websocket.client_state != WebSocketState.CONNECTED
            or websocket.application_state == WebSocketState.DISCONNECTED
        ):
            logger.warning("WebSocket not connected, cannot send message.")
            return
        try:
            await websocket.send_json(message)
        except Exception as e:
            # 连接已关闭或异常，忽略发送失败
            logger.error(f"Error sending JSON message: {e}, ignoring.")
            pass

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            if (
                connection.client_state == WebSocketState.CONNECTED
                and connection.application_state != WebSocketState.DISCONNECTED
            ):
                try:
                    await connection.send_text(message)
                except Exception as e:
                    # 忽略单个连接的发送失败
                    logger.error(f"Error broadcasting message: {e}, ignoring.")
                    pass


ws_manager = WebSocketManager()
