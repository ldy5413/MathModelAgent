# import redis
import redis.asyncio as aioredis
from app.config.setting import settings

# 配置 Redis
REDIS_URL = settings.REDIS_URL
# redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
redis_async_client = aioredis.Redis.from_url(REDIS_URL, decode_responses=True)
