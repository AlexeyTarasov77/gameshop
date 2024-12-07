import typing as t

from core.http.utils import save_upload_file
from core.service import BaseService
from gateways.db.exceptions import DatabaseError
from products.domain.interfaces import CategoriesRepositoryI, PlatformsRepositoryI, ProductsRepositoryI
from products.models import Product
from products.schemas import CreateProductDTO, ShowProduct, UpdateProductDTO


class ProductsService(BaseService):
    entity_name = "Product"

    async def create_product(self, dto: CreateProductDTO) -> ShowProduct:
        try:
            async with self.uow as uow:
                uploaded_to = await save_upload_file(dto.image)
                repo = t.cast(ProductsRepositoryI, uow.products_repo)
                product = await repo.create(dto, uploaded_to)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(
                **dto.model_dump(include=["name", "category_name", "platform_name"])
            ) from e
        return product.to_read_model()

    async def platforms_list(self) -> list[str]:
        async with self.uow as uow:
            repo = t.cast(PlatformsRepositoryI, uow.platforms_repo)
            platforms = await repo.list_names()
        return platforms

    async def categories_list(self) -> list[str]:
        async with self.uow as uow:
            repo = t.cast(CategoriesRepositoryI, uow.categories_repo)
            categories = await repo.list_names()
        return categories

    async def delivery_methods_list(self) -> list[str]:
        return list(Product.DELIVERY_METHODS_CHOICES)

    async def update_product(self, product_id: int, dto: UpdateProductDTO) -> ShowProduct:
        uploaded_to = None
        try:
            async with self.uow as uow:
                if dto.image:
                    uploaded_to = save_upload_file(dto.image)
                repo = t.cast(ProductsRepositoryI, uow.products_repo)
                product = await repo.update(dto, uploaded_to, id=product_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(
                **dto.model_dump(include=["name", "category_name", "platform_name"])
            ) from e
        return product.to_read_model()

    async def delete_product(self, product_id: int) -> None:
        try:
            async with self.uow as uow:
                repo = t.cast(ProductsRepositoryI, uow.products_repo)
                await repo.delete(product_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(id=product_id) from e
