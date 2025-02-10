import redis.asyncio as redis


class RedisClient:
    async def ping(self) -> None:
        await self.client.ping()

    def __init__(self, dsn: str):
        self._dsn = dsn
        self.client = redis.from_url(dsn)
