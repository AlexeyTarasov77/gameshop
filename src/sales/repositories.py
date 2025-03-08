import asyncio
import time
from collections.abc import AsyncGenerator, Sequence
from typing import Any
from uuid import UUID
from redis.asyncio import Redis

from core.pagination import PaginationParams, PaginationResT
from gateways.db.exceptions import DatabaseError, NotFoundError
from sales.schemas import ProductOnSaleDTO, SalesFilterDTO


class SalesRepository:
    def __init__(self, redis: Redis):
        self._db = redis
        self._prefix = "sales_item:"
        self._key = "sales"

    def _assert_not_none(self, res):
        if res is None:
            raise DatabaseError(
                "Redis query failed! Value under key is not a valid json array"
            )

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
        coros = [
            self._db.json().set(
                self._prefix + str(item.id), "$", item.model_dump(exclude={"id"})
            )
            for item in sales
        ]
        res = await asyncio.gather(*coros)
        assert all(res)

    def _build_filter_condition(self, dto: SalesFilterDTO) -> str:
        conditions: list[str] = []
        if dto.category is not None:
            conditions.append(f'category=~"(?i)^{dto.category}$"')
        if dto.region is not None:
            conditions.append(f"prices.{dto.region.lower()}")
        conditions_str = "&&".join([f"@.{cond}" for cond in conditions])
        return conditions_str

    async def filter_paginated_list(
        self,
        dto: SalesFilterDTO,
        pagination_params: PaginationParams,
    ) -> PaginationResT[dict[str, Any]]:
        filter_cond = self._build_filter_condition(dto)
        query = (
            f"$[?({filter_cond})]" if filter_cond else "$"
        )  # $[?(@.prices.tr && @.category=="PSN")
        res, total = await asyncio.gather(
            self._db.json().get(self._key, query),
            self._db.json().arrlen(self._key),  # type: ignore
        )
        self._assert_not_none(res)
        items = res[0] if query == "$" else res
        assert isinstance(items, list)
        offset = pagination_params.calc_offset()
        return items[offset : offset + pagination_params.page_size], total

    def _find_by_id_query(self, product_id: UUID) -> str:
        return f'$[?(@.id == "{product_id}")]'

    async def delete_by_id(self, product_id: UUID) -> None:
        success: int | None = await self._db.json().delete(
            self._key, self._find_by_id_query(product_id)
        )
        self._assert_not_none(success)
        if not success:
            raise NotFoundError()

    async def get_by_id(self, product_id: UUID) -> dict[str, Any]:
        res = await self._db.json().get(self._key, self._find_by_id_query(product_id))
        self._assert_not_none(res)
        if not res:
            raise NotFoundError()
        return res[0]
