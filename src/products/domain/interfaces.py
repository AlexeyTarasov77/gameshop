import typing as t

from products.models import Product
from products.schemas import CreateProductDTO


class ProductsRepositoryI(t.Protocol):
    async def create(self, dto: CreateProductDTO) -> Product: ...
