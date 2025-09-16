import asyncio
import json
import time
from typing import Optional

from pydantic import BaseModel

from app.services.redis_manager import redis_manager
from app.schemas.response import SystemMessage, UserMessage
from uuid import uuid4


CHECKPOINT_KEY_TPL = "task:{task_id}:checkpoint:{checkpoint_id}"
CHECKPOINT_HOLD_KEY_TPL = "task:{task_id}:checkpoint:{checkpoint_id}:hold"


class CheckpointAction(BaseModel):
    kind: str = "checkpoint"
    checkpoint_id: str
    timeout_sec: int = 10
    agent: str
    sub_title: Optional[str] = None


class CheckpointControl:
    @staticmethod
    async def prompt_and_wait(
        task_id: str,
        agent: str,
        sub_title: Optional[str] = None,
        timeout_sec: int = 10,
    ) -> Optional[str]:
        """
        发布检查点消息，等待用户在超时内的选择。

        返回：
            - None: 继续
            - str: 用户反馈内容，需要将其添加到对话历史，并重跑该步骤
        """
        checkpoint_id = str(uuid4())
        action = CheckpointAction(
            checkpoint_id=checkpoint_id,
            timeout_sec=timeout_sec,
            agent=agent,
            sub_title=sub_title,
        )

        # 推送交互式系统消息
        await redis_manager.publish_message(
            task_id,
            SystemMessage(
                content=(
                    f"{agent} 已完成一步{f'（{sub_title}）' if sub_title else ''}，请在 {timeout_sec}s 内选择：1) 继续  2) 用户反馈"
                ),
                action=action.model_dump(),
            ),
        )

        # 轮询等待用户响应（Redis Key）
        client = await redis_manager.get_client()
        key = CHECKPOINT_KEY_TPL.format(task_id=task_id, checkpoint_id=checkpoint_id)
        start_time = time.time()
        deadline = start_time + timeout_sec
        while True:
            val = await client.get(key)
            if val:
                try:
                    data = json.loads(val)
                except Exception:
                    data = {"action": "continue"}
                # 使用一次即清理
                try:
                    await client.delete(key)
                except Exception:
                    pass

                act = (data.get("action") or "continue").lower()
                if act == "feedback":
                    content = (data.get("content") or "").strip()
                    if content:
                        # 将用户反馈同步到对话栏
                        await redis_manager.publish_message(task_id, UserMessage(content=content))
                        return content
                    # 空内容则当继续
                    return None
                # 继续
                return None

            # 若进入反馈输入状态（前端已通知 hold），暂停倒计时，直到 hold 解除
            hold_key = CHECKPOINT_HOLD_KEY_TPL.format(task_id=task_id, checkpoint_id=checkpoint_id)
            in_hold = bool(await client.exists(hold_key))
            if in_hold:
                await asyncio.sleep(0.3)
                # 继续下一轮检查，不推进超时
                continue

            # 未 hold，正常走超时逻辑
            if time.time() >= deadline:
                return None
            await asyncio.sleep(0.2)

        # 超时自动继续
        return None
