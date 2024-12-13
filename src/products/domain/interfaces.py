import typing as t

from products.models import Category, Platform, Product
from products.schemas import CreateProductDTO, UpdateProductDTO


class ProductsRepositoryI(t.Protocol):
    async def create(self, dto: CreateProductDTO) -> Product: ...

    async def update(self, dto: UpdateProductDTO, **filter_params) -> Product: ...

    async def delete(self, product_id: int) -> None: ...

    async def paginated_list(self, limit: int, offset: int) -> list[Product]: ...

    async def get_records_count(self) -> int: ...


class PlatformsRepositoryI(t.Protocol):
    async def list(self) -> list[Platform]: ...


class CategoriesRepositoryI(t.Protocol):
    async def list(self) -> list[Category]: ...
