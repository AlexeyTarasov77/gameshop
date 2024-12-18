from gateways.db.repository import SqlAlchemyRepository
from sqlalchemy import select, text

from products.models import Category, Platform, Product, DeliveryMethod
from products.schemas import CreateProductDTO, UpdateProductDTO


class ProductsRepository(SqlAlchemyRepository[Product]):
    model = Product

    async def create(self, dto: CreateProductDTO) -> Product:
        product = await super().create(
            image_url=str(dto.image_url),
            category_id=dto.category.id,
            platform_id=dto.platform.id,
            delivery_method_id=dto.delivery_method.id,
            **dto.model_dump(
                exclude={"image_url", "category", "platform", "delivery_method"},
                exclude_none=True,
            ),
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
        if dto.delivery_method:
            data["delivery_method_id"] = dto.delivery_method.id
        product = await super().update(
            data,
            **filter_params,
        )
        return product

    async def delete(self, product_id: int) -> None:
        await super().delete(id=product_id)

    async def paginated_list(self, limit: int, offset: int) -> list[Product]:
        stmt = select(self.model).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get_records_count(self) -> int:
        stmt = text(f"SELECT COUNT(id) FROM {self.model.__tablename__}")
        res = await self.session.execute(stmt)
        return res.scalar()

    async def get_by_id(self, product_id: int) -> Product:
        return await super().get_one(id=product_id)


class PlatformsRepository(SqlAlchemyRepository[Platform]):
    model = Platform


class CategoriesRepository(SqlAlchemyRepository[Category]):
    model = Category


class DeliveryMethodsRepository(SqlAlchemyRepository[DeliveryMethod]):
    model = DeliveryMethod
