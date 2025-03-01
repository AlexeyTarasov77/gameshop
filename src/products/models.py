from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from gateways.db.column_types import created_at_type, int_pk_type, updated_at_type
from gateways.db.models import SqlAlchemyBaseModel
from sqlalchemy import ForeignKey, UniqueConstraint, text
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ProductOnSaleCategory(StrEnum):
    XBOX = "XBOX"
    PSN = "PSN"


class ProductOnSale(SqlAlchemyBaseModel):
    # __table_args__ = (UniqueConstraint("name", "category", "region"),)
    id: Mapped[int_pk_type]
    name: Mapped[str]
    base_price: Mapped[float]
    base_price_currency: Mapped[str]
    discounted_price: Mapped[float]
    discounted_price_currency: Mapped[str]
    deal_until: Mapped[datetime | None]
    image_url: Mapped[str]
    discount: Mapped[int]
    region: Mapped[str]
    with_gp: Mapped[bool | None]  # indicates whether discount is applied to game pass
    category: Mapped[ProductOnSaleCategory]


class Product(SqlAlchemyBaseModel):
    __table_args__ = (UniqueConstraint("name", "category_id", "platform_id"),)

    id: Mapped[int_pk_type]
    name: Mapped[str]
    description: Mapped[str]
    category_id: Mapped[int] = mapped_column(
        ForeignKey("category.id", ondelete="CASCADE")
    )
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platform.id", ondelete="CASCADE")
    )
    delivery_method_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_method.id", ondelete="CASCADE")
    )
    category: Mapped["Category"] = relationship(
        back_populates="products", lazy="joined"
    )
    platform: Mapped["Platform"] = relationship(
        back_populates="products", lazy="joined"
    )
    delivery_method: Mapped["DeliveryMethod"] = relationship(
        back_populates="products", lazy="joined"
    )
    image_url: Mapped[str]
    regular_price: Mapped[Decimal]
    in_stock: Mapped[bool] = mapped_column(server_default=text("true"))
    discount: Mapped[int] = mapped_column(server_default=text("0"))
    discount_valid_to: Mapped[datetime | None]
    created_at: Mapped[created_at_type]
    updated_at: Mapped[updated_at_type]

    @property
    def total_discount(self) -> int:
        discount = self.discount
        if self.discount_valid_to and (datetime.now() >= self.discount_valid_to):
            discount = 0
        return discount

    @property
    def total_price(self) -> Decimal:
        total = self.regular_price - (
            Decimal(self.total_discount / 100) * self.regular_price
        )
        return total.quantize(Decimal("0.01"), ROUND_HALF_UP)


class BaseRefModel(SqlAlchemyBaseModel):
    __abstract__ = True
    id: Mapped[int_pk_type]
    name: Mapped[str]
    url: Mapped[str] = mapped_column(unique=True)

    @declared_attr
    def products(self):
        return relationship(Product, back_populates=self.__tablename__)


class Category(BaseRefModel): ...


class Platform(BaseRefModel): ...


class DeliveryMethod(BaseRefModel): ...
