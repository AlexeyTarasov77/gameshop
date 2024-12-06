from datetime import datetime
from decimal import Decimal
from typing import Final

from gateways.db.column_types import created_at_t, int_pk_type, updated_at_t
from gateways.db.models import SqlAlchemyBaseModel
from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from products.schemas import ShowProduct


class Product(SqlAlchemyBaseModel):
    model_schema = ShowProduct

    DELIVERY_METHODS_CHOICES: Final[tuple[str]] = (
        "activation_key",
        "replenishment_card",
        "account_purchase",
    )
    __table_args__ = (
        CheckConstraint(
            text(f"delivery_method = ANY (ARRAY[{','.join(DELIVERY_METHODS_CHOICES)}]::text[])")
        ),
        UniqueConstraint("name", "category_name", "platform_name"),
    )

    id: Mapped[int_pk_type]
    name: Mapped[str]
    description: Mapped[str]
    category_name: Mapped[str] = mapped_column(ForeignKey("category.name", ondelete="CASCADE"))
    platform_name: Mapped[str] = mapped_column(ForeignKey("platform.name", ondelete="CASCADE"))
    category: Mapped["Category"] = relationship(back_populates="products")
    platform: Mapped["Platform"] = relationship(back_populates="products")
    image_url: Mapped[str]
    regular_price: Mapped[Decimal]
    delivery_method: Mapped[str]
    discount: Mapped[int] = mapped_column(default=0)
    discount_valid_to: Mapped[datetime | None]
    created_at: Mapped[created_at_t]
    updated_at: Mapped[updated_at_t]


class Category(SqlAlchemyBaseModel):
    name: Mapped[str] = mapped_column(primary_key=True)
    products: Mapped[list[Product]] = relationship(back_populates="category")


class Platform(SqlAlchemyBaseModel):
    name: Mapped[str] = mapped_column(primary_key=True)
    products: Mapped[list[Product]] = relationship(back_populates="platform")
