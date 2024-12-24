import typing as t

from products.models import Category, Platform, Product, DeliveryMethod
from products.schemas import CreateProductDTO, UpdateProductDTO


class ProductsRepositoryI(t.Protocol):
    async def create(self, dto: CreateProductDTO) -> Product: ...

    async def update_by_id(self, dto: UpdateProductDTO, product_id: int) -> Product: ...

    async def delete_by_id(self, product_id: int) -> None: ...

    async def paginated_list(self, limit: int, offset: int) -> t.Sequence[Product]: ...

    async def get_records_count(self) -> int: ...

    async def get_by_id(self, product_id: int) -> Product: ...


class PlatformsRepositoryI(t.Protocol):
    async def list(self) -> t.Sequence[Platform]: ...


class CategoriesRepositoryI(t.Protocol):
    async def list(self) -> t.Sequence[Category]: ...


class DeliveryMethodsRepositoryI(t.Protocol):
    async def list(self) -> t.Sequence[DeliveryMethod]: ...
