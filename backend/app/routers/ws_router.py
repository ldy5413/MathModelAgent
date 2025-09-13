from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from app.services.redis_manager import redis_manager
from app.schemas.response import SystemMessage
import asyncio
from app.services.ws_manager import ws_manager
import json
from app.utils.log_util import logger
router = APIRouter()


@router.websocket("/task/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    logger.info(f"WebSocket 尝试连接 task_id: {task_id}")

    redis_async_client = await redis_manager.get_client()
    if not await redis_async_client.exists(f"task_id:{task_id}"):
        logger.warning(f"Task not found: {task_id}")
        await websocket.close(code=1008, reason="Task not found")
        return
    logger.info(f"WebSocket connected for task: {task_id}")

    # 建立 WebSocket 连接
    await ws_manager.connect(websocket)
    websocket.timeout = 500
    logger.info(f"WebSocket connection status: {websocket.client}")

    # 订阅 Redis 频道
    pubsub = await redis_manager.subscribe_to_task(task_id)
    logger.info(f"Subscribed to Redis channel: task:{task_id}:messages")

    await redis_manager.publish_message(
        task_id,
        SystemMessage(content="任务开始处理"),
    )

    try:
        while True:
            try:
                msg = await pubsub.get_message(ignore_subscribe_messages=True)
                if msg:
                    print(f"Received message: {msg}")
                    try:
                        msg_dict = json.loads(msg["data"])
                        await ws_manager.send_personal_message_json(
                            msg_dict, websocket
                        )
                        logger.info(f"Sent message to WebSocket: {msg_dict}")
                    except Exception as e:
                        # 如果连接已关闭，退出循环，避免重复发送错误信息
                        logger.error(f"Error sending/parsing message: {e}")
                        break
                await asyncio.sleep(0.1)

            except WebSocketDisconnect:
                logger.warning("WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"Error in websocket loop: {e}")
                await asyncio.sleep(1)
                continue

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await pubsub.unsubscribe(f"task:{task_id}:messages")
        ws_manager.disconnect(websocket)
        logger.info(f"WebSocket connection closed for task: {task_id}")
