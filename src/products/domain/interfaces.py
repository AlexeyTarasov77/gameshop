import typing as t

from core.http.utils import FilePath
from products.models import Product
from products.schemas import CreateProductDTO, UpdateProductDTO


class ProductsRepositoryI(t.Protocol):
    async def create(self, dto: CreateProductDTO, image_url: FilePath) -> Product: ...

    async def update(
        self, dto: UpdateProductDTO, image_url: FilePath = None, **filter_params
    ) -> Product: ...

    async def delete(self, product_id: int) -> None: ...
