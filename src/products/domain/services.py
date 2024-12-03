import typing as t

from core.service import BaseService
from products.domain.interfaces import ProductsRepositoryI
from products.models import Product
from products.schemas import CreateProductDTO


class ProductsService(BaseService):
    async def create_product(self, dto: CreateProductDTO) -> Product:
        async with self.uow as uow:
            # TODO: Handle exceptions
            repo = t.cast(ProductsRepositoryI, uow.products_repo)
            product = await repo.create(dto)
        return product
