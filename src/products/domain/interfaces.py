from collections.abc import Sequence
import typing as t

from core.pagination import PaginationParams, PaginationResT
from products.models import (
    Category,
    Platform,
    Product,
    DeliveryMethod,
)
from products.schemas import (
    CreateProductDTO,
    ListProductsFilterDTO,
    ProductFromAPIDTO,
    UpdateProductDTO,
)


class ProductsAPIClient(t.Protocol):
    async def get_paginated(
        self, pagination_params: PaginationParams
    ) -> PaginationResT[ProductFromAPIDTO]: ...


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


class PlatformsRepositoryI(t.Protocol):
    async def list(self) -> Sequence[Platform]: ...


class CategoriesRepositoryI(t.Protocol):
    async def list(self) -> Sequence[Category]: ...


class DeliveryMethodsRepositoryI(t.Protocol):
    async def list(self) -> Sequence[DeliveryMethod]: ...
