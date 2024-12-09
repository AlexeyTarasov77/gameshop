from datetime import datetime
from decimal import Decimal
from typing import Final

from gateways.db.column_types import created_at_type, int_pk_type, updated_at_type
from gateways.db.models import SqlAlchemyBaseModel
from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from products.schemas import CategoryDTO, PlatformDTO, ShowProduct


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
        UniqueConstraint("name", "category_id", "platform_id"),
    )

    id: Mapped[int_pk_type]
    name: Mapped[str]
    description: Mapped[str]
    category_id: Mapped[str] = mapped_column(ForeignKey("category.id", ondelete="CASCADE"))
    platform_id: Mapped[str] = mapped_column(ForeignKey("platform.id", ondelete="CASCADE"))
    category: Mapped["Category"] = relationship(back_populates="products", lazy="joined")
    platform: Mapped["Platform"] = relationship(back_populates="products", lazy="joined")
    image_url: Mapped[str]
    regular_price: Mapped[Decimal]
    delivery_method: Mapped[str]
    discount: Mapped[int] = mapped_column(default=0)
    discount_valid_to: Mapped[datetime | None]
    created_at: Mapped[created_at_type]
    updated_at: Mapped[updated_at_type]


class Category(SqlAlchemyBaseModel):
    model_schema = CategoryDTO

    id: Mapped[int_pk_type]
    name: Mapped[str]
    products: Mapped[list[Product]] = relationship(back_populates="category")


class Platform(SqlAlchemyBaseModel):
    model_schema = PlatformDTO

    id: Mapped[int_pk_type]
    name: Mapped[str]
    products: Mapped[list[Product]] = relationship(back_populates="platform")
