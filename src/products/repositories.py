from gateways.db.repository import PaginationRepository, SqlAlchemyRepository
from sqlalchemy import select, text

from products.models import Category, Platform, Product, DeliveryMethod
from products.schemas import CreateProductDTO, UpdateProductDTO


class ProductsRepository(PaginationRepository[Product]):
    model = Product

    async def create(self, dto: CreateProductDTO) -> Product:
        product = await super().create(
            category_id=dto.category.id,
            platform_id=dto.platform.id,
            delivery_method_id=dto.delivery_method.id,
            **dto.model_dump(
                exclude={"category", "platform", "delivery_method"},
                exclude_none=True,
            ),
        )
        return product

    async def update_by_id(self, dto: UpdateProductDTO, product_id: int) -> Product:
        data = dto.model_dump(
            exclude={"image_url", "category", "platform", "delivery_method"},
            exclude_unset=True,
        )
        if dto.platform:
            data["platform_id"] = dto.platform.id
        if dto.category:
            data["category_id"] = dto.category.id
        if dto.delivery_method:
            data["delivery_method_id"] = dto.delivery_method.id
        product = await super().update(
            data,
            id=product_id,
        )
        return product

    async def delete_by_id(self, product_id: int) -> None:
        await super().delete(id=product_id)

    async def get_by_id(self, product_id: int) -> Product:
        return await super().get_one(id=product_id)


class PlatformsRepository(SqlAlchemyRepository[Platform]):
    model = Platform


class CategoriesRepository(SqlAlchemyRepository[Category]):
    model = Category


class DeliveryMethodsRepository(SqlAlchemyRepository[DeliveryMethod]):
    model = DeliveryMethod
