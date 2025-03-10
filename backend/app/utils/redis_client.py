import redis
import redis.asyncio as aioredis

# 配置 Redis
REDIS_URL = "redis://localhost:6379/0"
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
redis_async_client = aioredis.Redis.from_url(REDIS_URL)
