from collections.abc import Sequence
from decimal import Decimal
import typing as t

from core.pagination import PaginationParams, PaginationResT
from products.models import (
    Product,
    ProductCategory,
)
from products.schemas import (
    CreateProductDTO,
    ExchangeRatesMappingDTO,
    ListProductsFilterDTO,
    PriceUnitDTO,
    UpdateProductDTO,
    SetExchangeRateDTO,
)


class CurrencyConverterI(t.Protocol):
    async def convert_to_rub(self, price: PriceUnitDTO) -> Decimal: ...
    async def set_exchange_rate(self, dto: SetExchangeRateDTO): ...
    async def get_exchange_rates(self) -> ExchangeRatesMappingDTO: ...


class SteamAPIClientI(t.Protocol):
    async def get_currency_rates(self) -> ExchangeRatesMappingDTO: ...


class ProductsRepositoryI(t.Protocol):
    async def create_with_image(
        self, dto: CreateProductDTO, image_url: str
    ) -> Product: ...

    async def update_by_id(
        self, product_id: int, dto: UpdateProductDTO, image_url: str | None
    ) -> Product: ...

    async def delete_by_id(self, product_id: int) -> None: ...

    async def filter_paginated_list(
        self,
        dto: ListProductsFilterDTO,
        pagination_params: PaginationParams,
    ) -> PaginationResT[Product]: ...

    async def get_by_id(self, product_id: int) -> Product: ...

    async def check_in_stock(self, product_id: int) -> bool: ...

    async def list_by_ids(self, ids: Sequence[int]) -> Sequence[Product]: ...

    async def save_many(self, products: Sequence[Product]): ...

    async def delete_for_categories(self, categories: Sequence[ProductCategory]): ...
