import redis.asyncio as aioredis
from typing import Optional
from app.config.setting import settings
from app.schemas.response import AgentMessage


class RedisManager:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self._client: Optional[aioredis.Redis] = None

    async def get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
            )
        return self._client

    async def publish_message(self, task_id: str, message: AgentMessage):
        """发布消息到特定任务的频道"""
        client = await self.get_client()
        channel = f"task:{task_id}:messages"
        await client.publish(channel, message.model_dump_json())

    async def subscribe_to_task(self, task_id: str):
        """订阅特定任务的消息"""
        client = await self.get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(f"task:{task_id}:messages")
        return pubsub

    async def close(self):
        """关闭Redis连接"""
        if self._client:
            await self._client.close()
            self._client = None


redis_manager = RedisManager()
