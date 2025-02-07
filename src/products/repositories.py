from datetime import datetime

from sqlalchemy import and_, not_, or_
from core.utils import save_upload_file
from core.pagination import PaginationParams, PaginationResT
from gateways.db.repository import PaginationRepository, SqlAlchemyRepository

from products.models import Category, Platform, Product, DeliveryMethod, ProductOnSale
from products.schemas import CreateProductDTO, UpdateProductDTO


class ProductsRepository(PaginationRepository[Product]):
    model = Product

    async def filter_paginated_list_in_stock(
        self,
        query: str | None,
        category_id: int | None,
        discounted: bool | None,
        pagination_params: PaginationParams,
    ) -> PaginationResT[model]:
        stmt = super()._get_pagination_stmt(pagination_params)
        stmt = stmt.filter_by(in_stock=True)
        if query:
            stmt = stmt.where(self.model.name.ilike(f"%{query}%"))
        if category_id:
            stmt = stmt.filter_by(category_id=category_id)
        if discounted is not None:
            base_cond = and_(
                or_(
                    self.model.discount_valid_to.is_(None),
                    self.model.discount_valid_to >= datetime.now(),
                ),
                self.model.discount > 0,
            )

            if discounted is True:
                stmt = stmt.where(base_cond)
            else:
                stmt = stmt.where(not_(base_cond))

        res = await self.session.execute(stmt)
        return super()._split_records_and_count(res.all())

    async def create_and_save_upload(self, dto: CreateProductDTO) -> Product:
        image_url = await save_upload_file(dto.image)
        product = await super().create(
            category_id=dto.category.id,
            platform_id=dto.platform.id,
            delivery_method_id=dto.delivery_method.id,
            image_url=image_url,
            **dto.model_dump(
                exclude={"category", "platform", "delivery_method", "image"},
                exclude_none=True,
            ),
        )
        return product

    async def update_by_id(self, dto: UpdateProductDTO, product_id: int) -> Product:
        data = dto.model_dump(
            exclude={"image", "category", "platform", "delivery_method"},
            exclude_unset=True,
        )
        if dto.image:
            data["image_url"] = await save_upload_file(dto.image)
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

    async def update_in_stock(self, product_id: int, value: bool) -> None:
        await super().update({"in_stock": value}, id=product_id)

    async def delete_by_id(self, product_id: int) -> None:
        await super().delete_or_raise_not_found(id=product_id)

    async def get_by_id(self, product_id: int) -> Product:
        return await super().get_one(id=product_id)


class ProductOnSaleRepository(PaginationRepository[ProductOnSale]):
    model = ProductOnSale


class PlatformsRepository(SqlAlchemyRepository[Platform]):
    model = Platform


class CategoriesRepository(SqlAlchemyRepository[Category]):
    model = Category


class DeliveryMethodsRepository(SqlAlchemyRepository[DeliveryMethod]):
    model = DeliveryMethod
