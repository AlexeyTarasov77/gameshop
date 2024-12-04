import typing as t

from core.service import BaseService
from core.utils import FilePath
from products.domain.interfaces import ProductsRepositoryI
from products.schemas import CreateProductDTO, ShowProduct


class ProductsService(BaseService):
    async def create_product(self, dto: CreateProductDTO, image_url: FilePath) -> ShowProduct:
        async with self.uow as uow:
            # TODO: Handle exceptions
            repo = t.cast(ProductsRepositoryI, uow.products_repo)
            product = await repo.create(dto, image_url)
        return product.to_read_model()
