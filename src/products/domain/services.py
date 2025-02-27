from typing import cast
from core.pagination import PaginationParams, PaginationResT
from core.services.base import BaseService
from core.services.exceptions import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    EntityOperationRestrictedByRefError,
)
from core.utils import save_upload_file
from gateways.db.exceptions import (
    AlreadyExistsError,
    NotFoundError,
    OperationRestrictedByRefError,
)
from products.schemas import (
    CategoryDTO,
    DeliveryMethodDTO,
    CreateProductDTO,
    ListProductsFilterDTO,
    PlatformDTO,
    ProductOnSaleDTO,
    ShowProduct,
    ShowProductWithRelations,
    UpdateProductDTO,
)


class ProductsService(BaseService):
    entity_name = "Product"

    async def create_product(self, dto: CreateProductDTO) -> ShowProduct:
        try:
            async with self._uow as uow:
                product = await uow.products_repo.create_with_image(
                    dto, cast(str, dto.image)
                )
        except AlreadyExistsError as e:
            raise EntityAlreadyExistsError(
                self.entity_name,
                name=dto.name,
                category_id=dto.category.id,
                platform_id=dto.platform.id,
            ) from e
        return ShowProduct.model_validate(product)

    async def list_products(
        self,
        dto: ListProductsFilterDTO,
        pagination_params: PaginationParams,
    ) -> tuple[list[ShowProductWithRelations], int]:
        async with self._uow as uow:
            (
                products,
                total_records,
            ) = await uow.products_repo.filter_paginated_list(
                dto,
                pagination_params,
            )
        return [
            ShowProductWithRelations.model_validate(product) for product in products
        ], total_records

    async def get_current_sales(
        self, pagination_params: PaginationParams
    ) -> PaginationResT[ProductOnSaleDTO]:
        async with self._uow as uow:
            products, total_records = await uow.product_on_sale_repo.paginated_list(
                pagination_params,
            )
        return [
            ProductOnSaleDTO.model_validate(product) for product in products
        ], total_records

    async def get_product(self, product_id: int) -> ShowProductWithRelations:
        try:
            async with self._uow as uow:
                product = await uow.products_repo.get_by_id(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
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
                product = await uow.products_repo.update_by_id(
                    product_id, dto, cast(str | None, dto.image)
                )
        except AlreadyExistsError:
            params = {
                "name": dto.name,
                "category_id": dto.category.id if dto.category is not None else None,
                "platform_id": dto.platform.id if dto.platform is not None else None,
            }
            raise EntityAlreadyExistsError(
                self.entity_name, **{k: v for k, v in params.items() if v is not None}
            )
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
        return ShowProduct.model_validate(product)

    async def delete_product(self, product_id: int) -> None:
        try:
            async with self._uow as uow:
                await uow.products_repo.delete_by_id(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
        except OperationRestrictedByRefError:
            raise EntityOperationRestrictedByRefError(self.entity_name)
