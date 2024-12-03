import typing as t

from products.models import Product
from products.schemas import CreateProductDTO


class IProductService(t.Protocol):
    def create_product(self, dto: CreateProductDTO) -> Product: ...
