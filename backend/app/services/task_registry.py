import asyncio
from typing import Dict, Optional


class TaskRegistry:
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}

    def add(self, task_id: str, task: asyncio.Task):
        self._tasks[task_id] = task

    def get(self, task_id: str) -> Optional[asyncio.Task]:
        return self._tasks.get(task_id)

    def is_running(self, task_id: str) -> bool:
        t = self._tasks.get(task_id)
        return t is not None and not t.done()

    def cancel(self, task_id: str) -> bool:
        t = self._tasks.get(task_id)
        if t is None:
            return False
        if not t.done():
            t.cancel()
        return True

    def remove(self, task_id: str):
        self._tasks.pop(task_id, None)


task_registry = TaskRegistry()

