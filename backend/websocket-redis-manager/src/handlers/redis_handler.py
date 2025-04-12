from app.core.redis_manager import redis_async_client
import json

async def publish_message(task_id: str, message: dict):
    await redis_async_client.publish(f"task:{task_id}:messages", json.dumps(message))

async def subscribe_to_channel(task_id: str):
    pubsub = redis_async_client.pubsub()
    await pubsub.subscribe(f"task:{task_id}:messages")
    return pubsub