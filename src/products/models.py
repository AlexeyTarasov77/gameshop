from datetime import datetime
from decimal import Decimal

from gateways.db.column_types import created_at_type, int_pk_type, updated_at_type
from gateways.db.models import SqlAlchemyBaseModel
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, mapped_column, relationship

from products import schemas


class Product(SqlAlchemyBaseModel):
    model_schema = schemas.ShowProduct

    __table_args__ = (UniqueConstraint("name", "category_id", "platform_id"),)

    id: Mapped[int_pk_type]
    name: Mapped[str]
    description: Mapped[str]
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id", ondelete="CASCADE"))
    platform_id: Mapped[int] = mapped_column(ForeignKey("platform.id", ondelete="CASCADE"))
    delivery_method_id: Mapped[int] = mapped_column(ForeignKey("delivery_method.id", ondelete="CASCADE"))
    category: Mapped["Category"] = relationship(back_populates="products", lazy="joined")
    platform: Mapped["Platform"] = relationship(back_populates="products", lazy="joined")
    delivery_method: Mapped["DeliveryMethod"] = relationship(back_populates="products", lazy="joined")
    image_url: Mapped[str]
    regular_price: Mapped[Decimal]
    discount: Mapped[int] = mapped_column(default=0)
    discount_valid_to: Mapped[datetime | None]
    created_at: Mapped[created_at_type]
    updated_at: Mapped[updated_at_type]


class BaseRefModel(SqlAlchemyBaseModel):
    __abstract__ = True
    id: Mapped[int_pk_type]
    name: Mapped[str]
    url: Mapped[str] = mapped_column(unique=True)

    @declared_attr
    def products(self):
        return relationship(Product, back_populates=self.__tablename__)


class Category(BaseRefModel):
    model_schema = schemas.CategoryDTO


class Platform(BaseRefModel):
    model_schema = schemas.PlatformDTO


class DeliveryMethod(BaseRefModel):
    model_schema = schemas.DeliveryMethodDTO
