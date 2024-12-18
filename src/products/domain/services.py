import typing as t

from core.http.utils import PaginationParams
from core.service import BaseService
from gateways.db.exceptions import DatabaseError
from products.domain.interfaces import (
    CategoriesRepositoryI,
    PlatformsRepositoryI,
    ProductsRepositoryI,
    DeliveryMethodsRepositoryI,
)
from products.schemas import (
    CategoryDTO,
    DeliveryMethodDTO,
    CreateProductDTO,
    PlatformDTO,
    ShowProduct,
    ShowProductWithRelations,
    UpdateProductDTO,
)


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

    async def list_products(
        self, pagination_params: PaginationParams
    ) -> tuple[list[ShowProduct], int]:
        try:
            async with self.uow as uow:
                repo = t.cast(ProductsRepositoryI, uow.products_repo)
                products = await repo.paginated_list(
                    limit=pagination_params.page_size,
                    offset=pagination_params.page_size
                    * (pagination_params.page_num - 1),
                )
                total_records = await repo.get_records_count()
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)() from e
        return [
            ShowProductWithRelations.model_validate(product) for product in products
        ], total_records

    async def get_product(self, product_id: int) -> ShowProductWithRelations:
        try:
            async with self.uow as uow:
                repo = t.cast(ProductsRepositoryI, uow.products_repo)
                product = await repo.get_by_id(product_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)() from e
        return ShowProductWithRelations.model_validate(product)

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

    async def delivery_methods_list(self) -> list[DeliveryMethodDTO]:
        async with self.uow as uow:
            repo = t.cast(DeliveryMethodsRepositoryI, uow.categories_repo)
            delivery_methods = await repo.list()
        return [method.to_read_model() for method in delivery_methods]

    async def update_product(
        self, product_id: int, dto: UpdateProductDTO
    ) -> ShowProduct:
        try:
            async with self.uow as uow:
                repo = t.cast(ProductsRepositoryI, uow.products_repo)
                product = await repo.update(dto, id=product_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(
                **dto.model_dump(include=["name", "category_name", "platform_name"]),
                id=product_id,
            ) from e
        return product.to_read_model()

    async def delete_product(self, product_id: int) -> None:
        try:
            async with self.uow as uow:
                repo = t.cast(ProductsRepositoryI, uow.products_repo)
                await repo.delete(product_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(id=product_id) from e
