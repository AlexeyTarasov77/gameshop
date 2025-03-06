from collections.abc import Sequence
from redis.asyncio import Redis

from gateways.db.exceptions import DatabaseError
from sales.models import ProductOnSale


class SalesRepository:
    def __init__(self, redis: Redis):
        self._db = redis
        self._key = "sales"

    async def delete_all(self):
        await self._db.json().set(self._key, "$", [])

    async def create_many(self, sales: Sequence[ProductOnSale]):
        res = await self._db.json().arrappend(
            self._key, "$", *[item.as_json_serializable() for item in sales]
        )  # type: ignore
        if res is None:
            raise DatabaseError(
                "SalesRepository.create_many: value under key is not a json array"
            )
