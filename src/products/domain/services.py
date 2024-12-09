import typing as t

from core.service import BaseService
from gateways.db.exceptions import DatabaseError
from products.domain.interfaces import CategoriesRepositoryI, PlatformsRepositoryI, ProductsRepositoryI
from products.models import Product
from products.schemas import CategoryDTO, CreateProductDTO, PlatformDTO, ShowProduct, UpdateProductDTO


class ProductsService(BaseService):
    entity_name = "Product"

    async def create_product(self, dto: CreateProductDTO) -> ShowProduct:
        try:
            async with self.uow as uow:
                repo = t.cast(ProductsRepositoryI, uow.products_repo)
                product = await repo.create(dto)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(
                **dto.model_dump(include=["name", "category_name", "platform_name"])
            ) from e
        return product.to_read_model()

    async def platforms_list(self) -> list[PlatformDTO]:
        async with self.uow as uow:
            repo = t.cast(PlatformsRepositoryI, uow.platforms_repo)
            platforms = await repo.list()
        return platforms

    async def categories_list(self) -> list[CategoryDTO]:
        async with self.uow as uow:
            repo = t.cast(CategoriesRepositoryI, uow.categories_repo)
            categories = await repo.list()
        return [category.to_read_model() for category in categories]

    async def delivery_methods_list(self) -> list[str]:
        return list(Product.DELIVERY_METHODS_CHOICES)

    async def update_product(self, product_id: int, dto: UpdateProductDTO) -> ShowProduct:
        try:
            async with self.uow as uow:
                repo = t.cast(ProductsRepositoryI, uow.products_repo)
                product = await repo.update(dto, id=product_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(
                **dto.model_dump(include=["name", "category_name", "platform_name"]), id=product_id
            ) from e
        return product.to_read_model()

    async def delete_product(self, product_id: int) -> None:
        try:
            async with self.uow as uow:
                repo = t.cast(ProductsRepositoryI, uow.products_repo)
                await repo.delete(product_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(id=product_id) from e
