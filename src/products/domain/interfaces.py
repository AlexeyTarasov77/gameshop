import typing as t
from pathlib import Path

from products.models import Product
from products.schemas import CreateProductDTO, UpdateProductDTO


class ProductsRepositoryI(t.Protocol):
    async def create(self, dto: CreateProductDTO, image_url: Path) -> Product: ...

    async def update(
        self, dto: UpdateProductDTO, image_url: Path = None, **filter_params
    ) -> Product: ...

    async def delete(self, product_id: int) -> None: ...


class PlatformsRepositoryI(t.Protocol):
    async def list_names(self) -> list[str]: ...


class CategoriesRepositoryI(t.Protocol):
    async def list_names(self) -> list[str]: ...
