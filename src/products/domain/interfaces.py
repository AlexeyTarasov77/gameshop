from collections.abc import Sequence
from decimal import Decimal
import typing as t

from core.pagination import PaginationParams, PaginationResT
from products.models import (
    Category,
    Platform,
    Product,
    DeliveryMethod,
    ProductCategory,
)
from products.schemas import (
    CreateProductDTO,
    ExchangeRatesMappingDTO,
    ListProductsFilterDTO,
    PriceUnitDTO,
    ProductFromAPIDTO,
    UpdateProductDTO,
)
from sales.schemas import SetExchangeRateDTO


class SteamAPIClientI(t.Protocol):
    async def get_paginated_products(
        self, pagination_params: PaginationParams
    ) -> PaginationResT[ProductFromAPIDTO]: ...

    async def get_product_by_id(self, product_id: int) -> ProductFromAPIDTO: ...


class CurrencyConverterI(t.Protocol):
    async def convert_to_rub(self, price: PriceUnitDTO) -> Decimal: ...
    async def set_exchange_rate(self, dto: SetExchangeRateDTO): ...
    async def get_exchange_rates(self) -> ExchangeRatesMappingDTO: ...


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


class PlatformsRepositoryI(t.Protocol):
    async def list(self) -> Sequence[Platform]: ...


class CategoriesRepositoryI(t.Protocol):
    async def list(self) -> Sequence[Category]: ...


class DeliveryMethodsRepositoryI(t.Protocol):
    async def list(self) -> Sequence[DeliveryMethod]: ...
