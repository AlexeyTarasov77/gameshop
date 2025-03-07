from collections.abc import Sequence
from core.pagination import PaginationParams, PaginationResT
from sales.models import Currencies, PriceUnit, ProductOnSale
from sales.schemas import SalesFilterDTO
import typing as t


type ExchangeRatesMapping = dict[Currencies, float]


class CurrencyConverterI(t.Protocol):
    async def convert_to_rub(self, price: PriceUnit) -> PriceUnit: ...


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
