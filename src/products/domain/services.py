import typing as t

from core.service import BaseService
from products.domain.interfaces import ProductsRepositoryI
from products.schemas import CreateProductDTO, ShowProduct


class ProductsService(BaseService):
    async def create_product(self, dto: CreateProductDTO) -> ShowProduct:
        async with self.uow as uow:
            # TODO: Handle exceptions
            repo = t.cast(ProductsRepositoryI, uow.products_repo)
            print("repo", repo)
            product = await repo.create(dto)
        return product.to_read_model()
