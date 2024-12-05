import typing as t

from core.http.utils import save_upload_file
from core.service import BaseService, EntityRelatedResourceNotFoundError
from db.main import (
    DatabaseError,
    RelatedResourceNotFoundError,
)
from products.domain.interfaces import ProductsRepositoryI
from products.schemas import CreateProductDTO, ShowProduct

# class ProductsServiceError(Exception):
#     def _generate_msg(**kwargs) -> str:
#         return "Products service error"

#     def __init__(self, *args, **kwargs):
#         return super().__init__(self._generate_msg(**kwargs), *args)


# class ProductNotFoundError(ProductsServiceError):
#     def _generate_msg(self, **kwargs) -> str:
#         msg = "Product%snot found"
#         kwargs_string = " "
#         if kwargs:
#             kwargs_string = " with " + ", ".join(f"{key}={value}" for key, value in kwargs.items())
#         return msg % kwargs_string


# class ProductAlreadyExistsError(ProductsServiceError):
#     def _generate_msg(self, **kwargs) -> str:
#         msg = "Product%salready exists"
#         kwargs_string = " "
#         if kwargs:
#             kwargs_string += "with " + ", ".join(f"{key}={value}" for key, value in kwargs.items())
#         return msg % kwargs_string

#     def __init__(self, **kwargs) -> None:
#         super().__init__(self._generate_msg(**kwargs))


class ProductRelatedResourceNotFoundError(EntityRelatedResourceNotFoundError):
    def _generate_msg(self) -> str:
        return "Category or platform with specified name doesn't exist"


class ProductsService(BaseService):
    EXCEPTION_MAPPING = {
        **BaseService.EXCEPTION_MAPPING,
        RelatedResourceNotFoundError: ProductRelatedResourceNotFoundError,
    }
    entity_name = "Product"

    async def create_product(self, dto: CreateProductDTO) -> ShowProduct:
        try:
            async with self.uow as uow:
                uploaded_to = await save_upload_file(dto.image)
                repo = t.cast(ProductsRepositoryI, uow.products_repo)
                product = await repo.create(dto, uploaded_to)
        except DatabaseError as e:
            raise super().map_db_exception(e)(
                **dto.model_dump(include=["name", "category_name", "platform_name"])
            ) from e
        return product.to_read_model()
