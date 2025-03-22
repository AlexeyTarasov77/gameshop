from collections.abc import Sequence
from decimal import Decimal
import typing as t

from core.pagination import PaginationParams, PaginationResT
from gateways.currency_converter.schemas import (
    ExchangeRatesMappingDTO,
    SetExchangeRateDTO,
)
from products.models import (
    Product,
    ProductCategory,
)
from products.schemas import (
    CreateProductDTO,
    ListProductsFilterDTO,
    PriceUnitDTO,
    UpdateProductDTO,
)


class CurrencyConverterI(t.Protocol):
    async def convert_to_rub(self, price: PriceUnitDTO) -> Decimal: ...
    async def set_exchange_rate(self, dto: SetExchangeRateDTO): ...
    async def get_exchange_rates(self) -> ExchangeRatesMappingDTO: ...
    async def get_rate_for(
        self, rate_from: str, rate_to: str = "rub"
    ) -> float | None: ...


class ProductsRepositoryI(t.Protocol):
    async def create_with_price(
        self, dto: CreateProductDTO, base_price: Decimal
    ) -> Product: ...
    async def update_by_name(
        self, name: str, exclude_categories: Sequence[ProductCategory], **values
    ): ...
    async def save_ignore_conflict(self, product: Product): ...

    async def update_by_id_with_image(
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

    async def list_by_ids(
        self, ids: Sequence[int], *, only_in_stock: bool = False
    ) -> Sequence[Product]: ...

    async def save_many(self, products: Sequence[Product]): ...

    async def delete_for_categories(self, categories: Sequence[ProductCategory]): ...


class PricesRepositoryI(t.Protocol):
    async def add_price(self, for_product_id: int, base_price: Decimal) -> None: ...
    async def update_all_with_rate(
        self, for_currency: str, new_rate: float, old_rate: float
    ) -> None: ...
