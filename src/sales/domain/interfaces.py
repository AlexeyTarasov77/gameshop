from collections.abc import Sequence
from uuid import UUID
from core.pagination import PaginationParams, PaginationResT
from sales.models import Currencies, PriceUnit, ProductOnSale
from sales.schemas import ExchangeRateDTO, ProductOnSaleDTO, SalesFilterDTO
import typing as t


type ExchangeRatesMapping = dict[Currencies, float]


class CurrencyConverterI(t.Protocol):
    async def convert_to_rub(self, price: PriceUnit) -> PriceUnit: ...
    async def set_rub_exchange_rate(self, dto: ExchangeRateDTO): ...
    async def get_rub_exchange_rates(self) -> ExchangeRatesMapping: ...


class SalesRepositoryI(t.Protocol):
    async def filter_paginated_list(
        self,
        dto: SalesFilterDTO,
        pagination_params: PaginationParams,
    ) -> PaginationResT[ProductOnSale]: ...

    async def delete_by_id(self, product_id: UUID) -> None: ...

    async def get_by_id(self, product_id: UUID) -> ProductOnSale: ...

    async def delete_all(self): ...
    async def create_many(self, sales: Sequence[ProductOnSaleDTO]): ...
