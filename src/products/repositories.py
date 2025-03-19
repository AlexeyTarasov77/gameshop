from datetime import datetime
from sqlalchemy.sql.expression import cast
from collections.abc import Sequence
from decimal import Decimal
from sqlalchemy import String, and_, asc, delete, desc, not_, or_, select, func, update
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
    OrderByOption,
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
                    if not dto.regions
                    else Product.prices.and_(
                        func.lower(cast(RegionalPrice.region_code, String)).in_(
                            [region.lower() for region in dto.regions]
                        )
                    )
                )
            )
        )
        if dto.price_ordering:
            option = {OrderByOption.ASC: asc, OrderByOption.DESC: desc}[
                dto.price_ordering
            ]
            stmt = stmt.join(self.model.prices).order_by(
                option(RegionalPrice.base_price)
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
        if dto.categories:
            stmt = stmt.where(Product.category.in_(dto.categories))
        if dto.platforms:
            stmt = stmt.where(Product.platform.in_(dto.platforms))
        res = await self._session.execute(stmt)
        products = res.scalars().all()
        filtered_products = []
        for product in products:
            if not product.prices:
                continue
            if dto.delivery_methods and not any(
                m in dto.delivery_methods for m in product.delivery_methods
            ):
                continue
            filtered_products.append(product)

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

    async def list_by_ids(
        self, ids: Sequence[int], *, only_in_stock: bool = False
    ) -> Sequence[Product]:
        stmt = select(Product).where(Product.id.in_(ids))
        if only_in_stock:
            stmt = stmt.filter_by(in_stock=True)
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


class PricesRepository(SqlAlchemyRepository[RegionalPrice]):
    model = RegionalPrice

    async def add_price(self, for_product_id: int, base_price: Decimal) -> None:
        await super().create(product_id=for_product_id, base_price=base_price)

    async def update_with_rate(
        self, for_currency: str, new_rate: float, old_rate: float
    ) -> None:
        update_price_clause = RegionalPrice.base_price / old_rate * new_rate
        stmt = (
            update(self.model)
            .values(base_price=update_price_clause)
            .where(func.lower(self.model.converted_from_curr) == for_currency.lower())
        )
        await self._session.execute(stmt)
