import redis.asyncio as redis


def init_redis_client(dsn: str) -> redis.Redis:
    return redis.from_url(dsn)
