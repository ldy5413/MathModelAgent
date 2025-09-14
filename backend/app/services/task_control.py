from app.services.redis_manager import redis_manager
import asyncio
from app.schemas.response import SystemMessage


PAUSE_KEY_TPL = "task:{task_id}:paused"


class TaskControl:
    @staticmethod
    async def pause(task_id: str):
        client = await redis_manager.get_client()
        await client.set(PAUSE_KEY_TPL.format(task_id=task_id), "1")
        await redis_manager.publish_message(task_id, SystemMessage(content="任务已暂停", type="warning"))

    @staticmethod
    async def resume(task_id: str):
        client = await redis_manager.get_client()
        await client.delete(PAUSE_KEY_TPL.format(task_id=task_id))
        await redis_manager.publish_message(task_id, SystemMessage(content="任务已继续", type="info"))

    @staticmethod
    async def is_paused(task_id: str) -> bool:
        client = await redis_manager.get_client()
        return bool(await client.exists(PAUSE_KEY_TPL.format(task_id=task_id)))

    @staticmethod
    async def wait_if_paused(task_id: str, poll_interval: float = 0.5):
        """在暂停期间循环等待，复用同一 redis 连接以减少日志/开销"""
        client = await redis_manager.get_client()
        sent_notice = False
        key = PAUSE_KEY_TPL.format(task_id=task_id)
        while bool(await client.exists(key)):
            if not sent_notice:
                await redis_manager.publish_message(task_id, SystemMessage(content="当前任务处于暂停状态，等待继续…"))
                sent_notice = True
            await asyncio.sleep(poll_interval)
