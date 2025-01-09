from decimal import Decimal
from enum import Enum
from sqlalchemy import CheckConstraint, ForeignKey
from gateways.db.column_types import int_pk_type, created_at_type

from sqlalchemy.orm import Mapped, relationship, mapped_column
from gateways.db.models import SqlAlchemyBaseModel
from products.models import Product
from users.models import User


class OrderStatus(Enum):
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED "


class Order(SqlAlchemyBaseModel):
    __table_args__ = (CheckConstraint("email IS NOT NULL OR user_id IS NOT NULL"),)
    id: Mapped[int_pk_type]
    order_date: Mapped[created_at_type]
    customer_email: Mapped[str | None]
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )
    user: Mapped[User | None] = relationship(back_populates="orders")
    customer_phone: Mapped[str | None]
    customer_name: Mapped[str]
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    status: Mapped[OrderStatus] = mapped_column(default=OrderStatus.PENDING)

    def get_total(self):
        return sum(item.total_price for item in self.items)


class OrderItem(SqlAlchemyBaseModel):
    id: Mapped[int_pk_type]
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE")
    )
    product: Mapped[Product] = relationship()
    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"))
    order: Mapped[Order] = relationship(back_populates="items")
    price: Mapped[Decimal]
    quantity: Mapped[int] = mapped_column(CheckConstraint("quantity > 0"))

    @property
    def total_price(self):
        return self.price * self.quantity
