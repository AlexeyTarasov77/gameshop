from datetime import datetime

from collections.abc import Sequence
from sqlalchemy import and_, desc, not_, or_, select
from core.pagination import PaginationParams, PaginationResT
from gateways.db.repository import PaginationRepository, SqlAlchemyRepository

from products.models import Category, Platform, Product, DeliveryMethod, ProductOnSale
from products.schemas import CreateProductDTO, ListProductsFilterDTO, UpdateProductDTO


class ProductsRepository(PaginationRepository[Product]):
    model = Product

    async def filter_paginated_list(
        self,
        dto: ListProductsFilterDTO,
        pagination_params: PaginationParams,
    ) -> PaginationResT[model]:
        stmt = (
            super()
            ._get_pagination_stmt(pagination_params)
            .order_by(desc(Product.created_at))
        )
        if dto.query:
            stmt = stmt.where(self.model.name.ilike(f"%{dto.query}%"))
        if dto.category_id is not None:
            stmt = stmt.filter_by(category_id=dto.category_id)
        if dto.discounted is not None:
            base_cond = and_(
                or_(
                    self.model.discount_valid_to.is_(None),
                    self.model.discount_valid_to >= datetime.now(),
                ),
                self.model.discount > 0,
            )

            if dto.discounted is True:
                stmt = stmt.where(base_cond)
            else:
                stmt = stmt.where(not_(base_cond))
        if dto.in_stock is not None:
            stmt = stmt.filter_by(in_stock=dto.in_stock)

        res = await self.session.execute(stmt)
        return super()._split_records_and_count(res.all())

    async def create_with_image(self, dto: CreateProductDTO, image_url: str) -> Product:
        product = await super().create(
            category_id=dto.category.id,
            platform_id=dto.platform.id,
            delivery_method_id=dto.delivery_method.id,
            image_url=image_url,
            **dto.model_dump(
                exclude={"category", "platform", "delivery_method", "image"},
            ),
        )
        return product

    async def update_by_id(
        self, product_id: int, dto: UpdateProductDTO, image_url: str | None
    ) -> Product:
        data = dto.model_dump(
            exclude={"image", "category", "platform", "delivery_method"},
            exclude_unset=True,
        )
        if image_url:
            data["image_url"] = image_url
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
        await super().delete_or_raise_not_found(id=product_id)

    async def get_by_id(self, product_id: int) -> Product:
        return await super().get_one(id=product_id)

    async def list_by_ids(self, ids: Sequence[int]) -> Sequence[Product]:
        stmt = select(Product).where(Product.id.in_(ids))
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def check_in_stock(self, product_id: int) -> bool:
        stmt = select(Product.id).filter_by(id=product_id, in_stock=True)
        res = await self.session.execute(stmt)
        return bool(res.scalar_one_or_none())


class ProductOnSaleRepository(PaginationRepository[ProductOnSale]):
    model = ProductOnSale


class PlatformsRepository(SqlAlchemyRepository[Platform]):
    model = Platform


class CategoriesRepository(SqlAlchemyRepository[Category]):
    model = Category


class DeliveryMethodsRepository(SqlAlchemyRepository[DeliveryMethod]):
    model = DeliveryMethod
