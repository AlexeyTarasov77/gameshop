from core.pagination import PaginationParams
from core.service import BaseService
from gateways.db.exceptions import DatabaseError
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
            async with self._uow as uow:
                product = await uow.products_repo.create(dto)
        except DatabaseError as e:
            raise self._exception_mapper.map_with_entity(e)(
                **dto.model_dump(include={"name", "category_name", "platform_name"})
            ) from e
        return ShowProduct.model_validate(product)

    async def list_products(
        self,
        query: str | None,
        category_id: int | None,
        pagination_params: PaginationParams,
    ) -> tuple[list[ShowProductWithRelations], int]:
        try:
            async with self._uow as uow:
                products = await uow.products_repo.filter_paginated_list(
                    query.strip() if query else None, category_id, pagination_params
                )
                total_records = await uow.products_repo.get_records_count()
        except DatabaseError as e:
            raise self._exception_mapper.map_with_entity(e)() from e
        return [
            ShowProductWithRelations.model_validate(product) for product in products
        ], total_records

    async def get_product(self, product_id: int) -> ShowProductWithRelations:
        try:
            async with self._uow as uow:
                product = await uow.products_repo.get_by_id(product_id)
        except DatabaseError as e:
            raise self._exception_mapper.map_with_entity(e)() from e
        return ShowProductWithRelations.model_validate(product)

    async def platforms_list(self) -> list[PlatformDTO]:
        async with self._uow as uow:
            platforms = await uow.platforms_repo.list()
        return [PlatformDTO.model_validate(platform) for platform in platforms]

    async def categories_list(self) -> list[CategoryDTO]:
        async with self._uow as uow:
            categories = await uow.categories_repo.list()
        return [CategoryDTO.model_validate(category) for category in categories]

    async def delivery_methods_list(self) -> list[DeliveryMethodDTO]:
        async with self._uow as uow:
            delivery_methods = await uow.delivery_methods_repo.list()
        return [DeliveryMethodDTO.model_validate(method) for method in delivery_methods]

    async def update_product(
        self, product_id: int, dto: UpdateProductDTO
    ) -> ShowProduct:
        try:
            async with self._uow as uow:
                product = await uow.products_repo.update_by_id(dto, product_id)
        except DatabaseError as e:
            raise self._exception_mapper.map_with_entity(e)(
                **dto.model_dump(include={"name", "category_name", "platform_name"}),
                id=product_id,
            ) from e
        return ShowProduct.model_validate(product)

    async def delete_product(self, product_id: int) -> None:
        try:
            async with self._uow as uow:
                await uow.products_repo.delete_by_id(product_id)
        except DatabaseError as e:
            raise self._exception_mapper.map_with_entity(e)(id=product_id) from e
