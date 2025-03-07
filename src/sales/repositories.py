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

    async def delete_all(self):
        await self._db.json().set(self._key, "$", [])

    async def create_many(self, sales: Sequence[ProductOnSaleDTO]):
        res = await self._db.json().arrappend(
            self._key, "$", *[item.model_dump() for item in sales]
        )  # type: ignore
        if res is None:
            raise DatabaseError(
                "SalesRepository.create_many: value under key is not a json array"
            )

    async def filter_paginated_list(
        self,
        dto: SalesFilterDTO,
        pagination_params: PaginationParams,
    ) -> PaginationResT[dict[str, Any]]:
        offset = pagination_params.calc_offset()
        items, total = await asyncio.gather(
            self._db.json().get(
                self._key, f"$[{offset}:{offset+pagination_params.page_size}]"
            ),
            self._db.json().arrlen(self._key),  # type: ignore
        )
        assert isinstance(items, list)
        return items, total
