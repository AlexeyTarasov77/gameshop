
from gateways.db.repository import SqlAlchemyRepository

from products.models import Category, Platform, Product
from products.schemas import CreateProductDTO, UpdateProductDTO


class ProductsRepository(SqlAlchemyRepository[Product]):
    model = Product

    async def create(self, dto: CreateProductDTO) -> Product:
        product = await super().create(
            image_url=str(dto.image_url),
            category_id=dto.category.id,
            platform_id=dto.platform.id,
            **dto.model_dump(exclude={"image_url", "category", "platform"}),
        )
        return product

    async def update(self, dto: UpdateProductDTO, **filter_params) -> Product:
        data = {
            **dto.model_dump(
                exclude={"image_url", "category", "platform"},
                exclude_unset=True,
            ),
        }
        if dto.image_url:
            data["image_url"] = str(dto.image_url)
        if dto.platform:
            data["platform_id"] = dto.platform.id
        if dto.category:
            data["category_id"] = dto.category.id
        product = await super().update(
            data,
            **filter_params,
        )
        return product

    async def delete(self, product_id: int) -> None:
        await super().delete(id=product_id)


class PlatformsRepository(SqlAlchemyRepository[Platform]):
    model = Platform


class CategoriesRepository(SqlAlchemyRepository[Category]):
    model = Category
