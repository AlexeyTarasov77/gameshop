from typing import NamedTuple
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql.expression import cast
from collections.abc import Sequence
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import selectinload
from core.api.pagination import PaginationResT
from core.api.schemas import OrderByOption
from core.utils import normalize_s
from gateways.db.sqlalchemy_gateway import PaginationRepository

from gateways.db.sqlalchemy_gateway.repository import SqlAlchemyRepository
from products.models import (
    Product,
    ProductPlatform,
    RegionalPrice,
)
from products.schemas import (
    CreateProductDTO,
    ListProductsParamsDTO,
    UpdateProductDTO,
)


class ProductsRepository(PaginationRepository[Product]):
    model = Product

    def _is_deal_until_expired_stmt(self):
        return sa.func.now().op("at time zone")("UTC") >= self.model.deal_until.op(
            "at time zone"
        )("UTC")

    async def filter_paginated_list(
        self,
        params: ListProductsParamsDTO,
    ) -> PaginationResT[Product]:
        stmt = (
            sa.select(self.model)
            .order_by(sa.desc(Product.created_at))
            .options(
                selectinload(
                    Product.prices
                    if not params.regions
                    else Product.prices.and_(
                        sa.func.lower(cast(RegionalPrice.region_code, sa.String)).in_(
                            [region.lower() for region in params.regions]
                        )
                    )
                )
            )
        )
        if params.price_ordering:
            option = {OrderByOption.ASC: sa.asc, OrderByOption.DESC: sa.desc}[
                params.price_ordering
            ]
            stmt = stmt.join(self.model.prices).order_by(
                option(RegionalPrice.base_price)
            )
        if params.query:
            stmt = stmt.where(self.model.name.ilike(f"%{params.query}%"))
        if params.discounted is not None:
            base_cond = sa.and_(
                sa.or_(
                    self.model.deal_until.is_(None),
                    sa.not_(self._is_deal_until_expired_stmt()),
                ),
                self.model.discount > 0,
            )
            stmt = stmt.where(base_cond if params.discounted else sa.not_(base_cond))
        if params.in_stock is not None:
            stmt = stmt.filter_by(in_stock=params.in_stock)
        if params.categories:
            stmt = stmt.where(Product.category.in_(params.categories))
        if params.platforms:
            stmt = stmt.where(Product.platform.in_(params.platforms))
        if params.delivery_methods:
            stmt = stmt.where(Product.delivery_method.in_(params.delivery_methods))
        res = await self._session.execute(stmt)
        products = res.scalars().all()
        filtered_products = []
        for product in products:
            if product.prices:
                filtered_products.append(product)

        offset = params.calc_offset()
        return filtered_products[offset : offset + params.page_size], len(
            filtered_products
        )

    async def get_all_in_stock(self) -> list[Product]:
        res = await super().list(in_stock=True)
        return list(res)

    async def create_with_price(
        self,
        dto: CreateProductDTO,
        base_price: Decimal,
        original_curr: str | None = None,
    ) -> Product:
        product = Product(
            image_url=dto.image,
            **dto.model_dump(
                exclude={"image", "discounted_price"},
            ),
            prices=[
                RegionalPrice(
                    base_price=base_price,
                    original_curr=normalize_s(original_curr) if original_curr else None,
                )
            ],
        )
        self._session.add(product)
        await self._session.flush()
        return product

    async def fetch_ids_for_platforms(
        self,
        platforms: Sequence[ProductPlatform],
    ) -> Sequence[int]:
        stmt = sa.select(Product.id).where(
            sa.and_(
                Product.platform.in_(platforms),
            )
        )
        res = await self._session.execute(stmt)
        return res.scalars().all()

    async def update_by_id_with_image(
        self, product_id: int, dto: UpdateProductDTO, image_url: str | None
    ) -> Product:
        data = dto.model_dump(
            exclude={"image", "base_price"},
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
        stmt = sa.select(Product).where(Product.id.in_(ids))
        if only_in_stock:
            stmt = stmt.filter_by(in_stock=True)
        res = await self._session.execute(stmt)
        return res.scalars().all()

    async def check_in_stock(self, product_id: int) -> bool:
        stmt = sa.select(Product.id).filter_by(id=product_id, in_stock=True)
        res = await self._session.execute(stmt)
        return bool(res.scalar_one_or_none())

    async def update_from_rows(self, rows: Sequence[NamedTuple]):
        if not rows:
            raise ValueError("Nothing to update")
        assert "id" in rows[0]._fields, "Id must be present in the row"
        columns = [sa.column(name) for name in rows[0]._fields]
        p2 = sa.values(*columns).data(rows).alias("p2")
        values = dict(p2.c)
        values.pop("id")
        stmt = sa.update(self.model).values(**values).where(self.model.id == p2.c.id)
        await self._session.execute(stmt)

    async def save_ignore_conflict(self, product: Product) -> int | None:
        product_data = {k: v for k, v in product.dump().items() if v is not None}
        res = await self._session.execute(
            insert(self.model)
            .values(**product_data)
            .on_conflict_do_nothing(index_elements=Product.unique_fields)
            .returning(Product.id)
        )
        product_id = res.scalar_one_or_none()
        if product_id is not None:  # inserted
            await self._session.execute(
                insert(RegionalPrice),
                [
                    {**price.dump(), "product_id": product_id}
                    for price in product.prices
                ],
            )
            return product_id
        return None

    async def save_on_conflict_update_discount(self, product: Product) -> int | None:
        product_data = {k: v for k, v in product.dump().items() if v is not None}
        res = await self._session.execute(
            insert(self.model)
            .values(**product_data)
            .on_conflict_do_update(
                index_elements=Product.unique_fields,
                set_={"discount": product.discount, "deal_until": product.deal_until},
            )
            .returning(
                Product.id, sa.text("xmax=0")
            ),  # xmax is a postgres specific field, which indicates whether row was deleted (updated)
        )
        product_id, inserted = res.all()[0]
        if inserted:
            await self._session.execute(
                insert(RegionalPrice),
                [
                    {**price.dump(), "product_id": product_id}
                    for price in product.prices
                ],
            )
            return product_id
        return None

    async def update_where_expired_discount(self, **values) -> int:
        stmt = (
            sa.update(self.model)
            .where(
                sa.and_(
                    self.model.deal_until.isnot(None),
                    self._is_deal_until_expired_stmt(),
                ),
            )
            .values(**values)
        )
        res = await self._session.execute(stmt)
        return res.rowcount


class PricesRepository(SqlAlchemyRepository[RegionalPrice]):
    model = RegionalPrice

    async def add_price(self, for_product_id: int, base_price: Decimal) -> None:
        await super().create(product_id=for_product_id, base_price=base_price)

    async def update_all_with_rate(
        self, for_currency: str, new_rate: Decimal, old_rate: Decimal
    ) -> None:
        update_price_clause = RegionalPrice.base_price / old_rate * new_rate
        stmt = (
            sa.update(self.model)
            .values(base_price=update_price_clause)
            .where(sa.func.lower(self.model.original_curr) == for_currency.lower())
        )
        await self._session.execute(stmt)

    async def add_percent_for_products(
        self, products_ids: Sequence[int], percent: int
    ) -> int:
        stmt = (
            sa.update(self.model)
            .where(self.model.product_id.in_(products_ids))
            .values(
                base_price=self.model.base_price + self.model.base_price / 100 * percent
            )
        )
        res = await self._session.execute(stmt)
        return res.rowcount

    async def get_price_for_region(
        self, product_id: int, region: str
    ) -> RegionalPrice | None:
        stmt = sa.select(self.model).where(
            sa.and_(
                sa.func.lower(sa.func.trim(self.model.region_code))
                == normalize_s(region),
                self.model.product_id == product_id,
            )
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def update_for_product(self, product_id: int, new_price: Decimal) -> None:
        await super().update({"base_price": new_price}, product_id=product_id)
