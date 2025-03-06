from collections.abc import Sequence
from core.pagination import PaginationParams, PaginationResT
from sales.models import ProductOnSale
from sales.schemas import SalesFilterDTO
import typing as t


class SalesRepositoryI(t.Protocol):
    # async def filter_paginated_list(
    #     self,
    #     dto: SalesFilterDTO,
    #     pagination_params: PaginationParams,
    # ) -> PaginationResT[ProductOnSale]: ...
    #
    # async def delete_by_id(self, product_id: int) -> None: ...
    #
    # async def get_by_id(self, product_id: int) -> ProductOnSale: ...

    async def delete_all(self): ...
    async def create_many(self, sales: Sequence[ProductOnSale]): ...
