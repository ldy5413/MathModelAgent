from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from app.utils.redis_client import redis_async_client
from app.schemas.response import AgentMessage, AgentType
import asyncio
from app.utils.connection import manager


router = APIRouter()


@router.websocket("/task/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    print(f"WebSocket 尝试连接 task_id: {task_id}")
    if not redis_async_client.exists(f"task_id:{task_id}"):
        print(f"Task not found: {task_id}")
        await websocket.close(code=1008, reason="Task not found")
        return
    print(f"WebSocket connected for task: {task_id}")

    await manager.connect(websocket)
    websocket.timeout = 500
    print(f"WebSocket connection status: {websocket.client}")

    pubsub = redis_async_client.pubsub()
    await pubsub.subscribe(f"task:{task_id}:messages")
    print(f"Subscribed to Redis channel: task:{task_id}:messages")

    # 修改这里，使用异步的 redis_async_client
    await redis_async_client.publish(
        f"task:{task_id}:messages",
        AgentMessage(
            agent_type=AgentType.SYSTEM, content="任务开始处理aaa"
        ).model_dump_json(),
    )

    try:
        while True:
            try:
                msg = await pubsub.get_message(ignore_subscribe_messages=True)
                if msg:
                    print(f"Received message: {msg}")
                    try:
                        agent_msg = AgentMessage.model_validate_json(msg["data"])
                        await websocket.send_json(agent_msg.model_dump())
                        print(f"Sent message to WebSocket: {agent_msg}")
                    except Exception as e:
                        print(f"Error parsing message: {e}")
                        await websocket.send_json({"error": str(e)})
                await asyncio.sleep(0.1)

            except WebSocketDisconnect:
                print("WebSocket disconnected")
                break
            except Exception as e:
                print(f"Error in websocket loop: {e}")
                await asyncio.sleep(1)
                continue

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await pubsub.unsubscribe(f"task:{task_id}:messages")
        manager.disconnect(websocket)
        print(f"WebSocket connection closed for task: {task_id}")
