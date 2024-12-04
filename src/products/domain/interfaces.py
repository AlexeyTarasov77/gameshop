import typing as t

from core.utils import FilePath
from products.models import Product
from products.schemas import CreateProductDTO


class ProductsRepositoryI(t.Protocol):
    async def create(self, dto: CreateProductDTO, image_url: FilePath) -> Product: ...
