from datetime import datetime

from collections.abc import Sequence
from decimal import Decimal
from sqlalchemy import and_, delete, desc, not_, or_, select, func
from sqlalchemy.orm import selectinload
from core.pagination import PaginationParams, PaginationResT
from gateways.db.sqlalchemy_gateway import PaginationRepository

from gateways.db.sqlalchemy_gateway.repository import SqlAlchemyRepository
from products.models import (
    Product,
    ProductCategory,
    RegionalPrice,
)
from products.schemas import (
    CreateProductDTO,
    ListProductsFilterDTO,
    UpdateProductDTO,
)


class ProductsRepository(PaginationRepository[Product]):
    model = Product

    async def filter_paginated_list(
        self,
        dto: ListProductsFilterDTO,
        pagination_params: PaginationParams,
    ) -> PaginationResT[model]:
        stmt = (
            select(self.model)
            .order_by(desc(Product.created_at))
            .options(
                selectinload(
                    Product.prices
                    if dto.region is None
                    else Product.prices.and_(
                        func.lower(RegionalPrice.region_code) == dto.region.lower()
                    )
                )
            )
        )
        if dto.query:
            stmt = stmt.where(self.model.name.ilike(f"%{dto.query}%"))
        if dto.discounted is not None:
            base_cond = and_(
                or_(
                    self.model.deal_until.is_(None),
                    self.model.deal_until >= datetime.now(),
                ),
                self.model.discount > 0,
            )
            stmt = stmt.where(base_cond if dto.discounted else not_(base_cond))
        if dto.in_stock is not None:
            stmt = stmt.filter_by(in_stock=dto.in_stock)
        if dto.category is not None:
            stmt = stmt.where(func.lower(Product.category) == dto.category.name.lower())
        res = await self._session.execute(stmt)
        products = res.scalars().all()
        filtered_products = [rec for rec in products if rec.prices]
        offset = pagination_params.calc_offset()
        return filtered_products[offset : offset + pagination_params.page_size], len(
            filtered_products
        )

    async def create_with_dto(self, dto: CreateProductDTO) -> Product:
        product = await super().create(
            image_url=dto.image,
            **dto.model_dump(
                exclude={"image", "discounted_price"},
            ),
        )
        return product

    async def update_by_id(
        self, product_id: int, dto: UpdateProductDTO, image_url: str | None
    ) -> Product:
        data = dto.model_dump(
            exclude={"image"},
            exclude_unset=True,
        )
        if image_url:
            data["image_url"] = image_url
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
        res = await self._session.execute(stmt)
        return res.scalars().all()

    async def check_in_stock(self, product_id: int) -> bool:
        stmt = select(Product.id).filter_by(id=product_id, in_stock=True)
        res = await self._session.execute(stmt)
        return bool(res.scalar_one_or_none())

    async def save_many(self, products: Sequence[Product]):
        self._session.add_all(products)
        await self._session.flush()

    async def delete_for_categories(self, categories: Sequence[ProductCategory]):
        stmt = delete(Product).where(Product.category.in_(categories))
        await self._session.execute(stmt)


class PricesRepository(SqlAlchemyRepository):
    model = RegionalPrice

    async def add_price(self, for_product_id: int, base_price: Decimal) -> None:
        await super().create(product_id=for_product_id, base_price=base_price)
