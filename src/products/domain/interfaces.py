import typing as t

from core.pagination import PaginationParams
from products.models import Category, Platform, Product, DeliveryMethod
from products.schemas import CreateProductDTO, UpdateProductDTO


class ProductsRepositoryI(t.Protocol):
    async def create(self, dto: CreateProductDTO) -> Product: ...

    async def update_by_id(self, dto: UpdateProductDTO, product_id: int) -> Product: ...

    async def delete_by_id(self, product_id: int) -> None: ...

    async def filter_paginated_list(
        self,
        query: str | None,
        category_id: int | None,
        pagination_params: PaginationParams,
    ) -> t.Sequence[Product]: ...

    async def get_records_count(self) -> int: ...

    async def get_by_id(self, product_id: int) -> Product: ...


class PlatformsRepositoryI(t.Protocol):
    async def list(self) -> t.Sequence[Platform]: ...


class CategoriesRepositoryI(t.Protocol):
    async def list(self) -> t.Sequence[Category]: ...


class DeliveryMethodsRepositoryI(t.Protocol):
    async def list(self) -> t.Sequence[DeliveryMethod]: ...
