from collections.abc import Sequence
from decimal import Decimal
import typing as t

from core.pagination import PaginationResT
from gateways.currency_converter.schemas import (
    ExchangeRatesMappingDTO,
    SetExchangeRateDTO,
)
from products.models import (
    Product,
    ProductPlatform,
    RegionalPrice,
)
from products.schemas import (
    CreateProductDTO,
    ListProductsParamsDTO,
    PriceUnitDTO,
    UpdateProductDTO,
)


class SavedGameInfo(t.NamedTuple):
    inserted_id: int
    url: str


class CurrencyConverterI(t.Protocol):
    async def convert_price(
        self, price: PriceUnitDTO, to_curr: str = "rub"
    ) -> PriceUnitDTO: ...
    async def set_exchange_rate(self, dto: SetExchangeRateDTO): ...
    async def get_exchange_rates(self) -> ExchangeRatesMappingDTO: ...
    async def get_rate_for(
        self, rate_from: str, rate_to: str = "rub"
    ) -> Decimal | None: ...


class ProductsRepositoryI(t.Protocol):
    async def create_with_price(
        self,
        dto: CreateProductDTO,
        base_price: Decimal,
        original_curr: str | None = None,
    ) -> Product: ...
    async def save_on_conflict_update_discount(
        self, product: Product
    ) -> int | None: ...

    async def save_ignore_conflict(self, product: Product) -> int | None: ...

    async def update_by_id_with_image(
        self, product_id: int, dto: UpdateProductDTO, image_url: str | None
    ) -> Product: ...

    async def delete_by_id(self, product_id: int) -> None: ...

    async def fetch_ids_for_platforms(
        self, platforms: Sequence[ProductPlatform]
    ) -> Sequence[int]: ...

    async def filter_paginated_list(
        self,
        params: ListProductsParamsDTO,
    ) -> PaginationResT[Product]: ...

    async def get_by_id(self, product_id: int) -> Product: ...

    async def check_in_stock(self, product_id: int) -> bool: ...

    async def list_by_ids(
        self, ids: Sequence[int], *, only_in_stock: bool = False
    ) -> Sequence[Product]: ...

    async def update_where_expired_discount(self, **values) -> int: ...
    async def update_from_rows(self, rows: Sequence[t.NamedTuple]): ...


class PricesRepositoryI(t.Protocol):
    async def add_price(self, for_product_id: int, base_price: Decimal) -> None: ...
    async def update_all_with_rate(
        self, for_currency: str, new_rate: Decimal, old_rate: Decimal
    ) -> None: ...
    async def add_percent_for_products(
        self,
        products_ids: Sequence[int],
        percent: int,
    ) -> int: ...
    async def get_price_for_region(
        self, product_id: int, region: str
    ) -> RegionalPrice | None: ...
    async def update_for_product(self, product_id: int, new_price: Decimal) -> None: ...
