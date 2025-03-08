import asyncio
from collections.abc import Sequence
from typing import Any
from redis.asyncio import Redis

from core.pagination import PaginationParams, PaginationResT
from gateways.db.exceptions import DatabaseError
from sales.schemas import ProductOnSaleDTO, SalesFilterDTO


class SalesRepository:
    def __init__(self, redis: Redis):
        self._db = redis
        self._key = "sales"

    def _assert_not_none(self, res):
        if res is None:
            raise DatabaseError(
                "Redis query failed! Value under key is not a valid json array"
            )

    async def delete_all(self):
        await self._db.json().set(self._key, "$", [])

    async def create_many(self, sales: Sequence[ProductOnSaleDTO]):
        res = await self._db.json().arrappend(
            self._key, "$", *[item.model_dump() for item in sales]
        )  # type: ignore
        self._assert_not_none(res)

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
