import typing as t

from core.http.utils import save_upload_file
from core.service import BaseService, EntityRelatedResourceNotFoundError
from core.uow import AbstractUnitOfWork
from db.exceptions import DatabaseError, RelatedResourceNotFoundError
from products.domain.interfaces import ProductsRepositoryI
from products.schemas import CreateProductDTO, ShowProduct, UpdateProductDTO


class ProductRelatedResourceNotFoundError(EntityRelatedResourceNotFoundError):
    def _generate_msg(self) -> str:
        return "Category or platform with specified name doesn't exist"


class ProductsService(BaseService):
    entity_name = "Product"

    def __init__(self, uow: AbstractUnitOfWork):
        super().__init__(uow)
        self.exception_mapper.EXCEPTION_MAPPING[RelatedResourceNotFoundError] = (
            ProductRelatedResourceNotFoundError
        )

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

    async def update_product(
        self, product_id: int, dto: UpdateProductDTO
    ) -> ShowProduct:
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
