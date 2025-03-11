import asyncio
import json
import time
from collections.abc import AsyncGenerator, Sequence

from redis.commands.search.query import Query
from uuid import UUID

from core.pagination import PaginationParams, PaginationResT
from gateways.db.exceptions import NotFoundError
from gateways.db.redis_gateway import AvailableIndexes
from gateways.db import RedisClient
from sales.models import ProductOnSale
from sales.schemas import ProductOnSaleDTO, SalesFilterDTO


class SalesRepository:
    def __init__(self, redis: RedisClient):
        self._db = redis
        self._prefix = AvailableIndexes.SALES_IDX.value.for_prefix
        self._idx = AvailableIndexes.SALES_IDX.value.name
        self._key = "sales"

    async def _scan_keys(self, count: int = 100) -> AsyncGenerator[list[str]]:
        cur: int | None = None
        match = self._prefix + "*"
        while cur != 0:
            cur, keys = await self._db.scan(cur or 0, match, count)
            time.sleep(1)
            yield keys

    async def delete_all(self):
        coros = [
            asyncio.gather(*[self._db.delete(key) for key in key_list])
            async for key_list in self._scan_keys()
        ]
        await asyncio.gather(*coros)

    async def create_many(self, sales: Sequence[ProductOnSaleDTO]):
        async def coro(item, i):
            print("CREATING", i)
            await self._db.json().set(
                self._prefix + str(item.id), "$", item.model_dump(exclude={"id"})
            )

        coros = [coro(item, i) for i, item in enumerate(sales)]
        res = await asyncio.gather(*coros)
        assert all(res)

    async def filter_paginated_list(
        self,
        dto: SalesFilterDTO,
        pagination_params: PaginationParams,
    ) -> PaginationResT[ProductOnSale]:
        conditions: list[str] = []
        if dto.category is not None:
            conditions.append("@category:{%s}" % dto.category)
        if dto.region is not None:
            conditions.append("@price_regions:{%s}" % dto.region)
        res = await self._db.ft(self._idx).search(  # type: ignore
            Query(" ".join(conditions) or "*").paging(
                pagination_params.calc_offset(), pagination_params.page_size
            )
        )
        products = []
        for doc in res.docs:
            product_id = UUID(doc.id[len(self._prefix) :])
            other_fields = json.loads(doc.json)
            products.append(ProductOnSale(id=product_id, **other_fields))
        return products, res.total

    def _build_key_by_id(self, product_id: UUID) -> str:
        return self._prefix + str(product_id)

    async def delete_by_id(self, product_id: UUID) -> None:
        deleted = await self._db.delete(self._build_key_by_id(product_id))
        if not deleted:
            raise NotFoundError()

    async def get_by_id(self, product_id: UUID) -> ProductOnSale:
        item_data = await self._db.json().get(self._build_key_by_id(product_id))
        if not item_data:
            raise NotFoundError()
        return ProductOnSale(id=product_id, **item_data)
