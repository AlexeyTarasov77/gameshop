from decimal import Decimal
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from uuid import UUID
from enum import Enum
from sqlalchemy import CheckConstraint, ForeignKey, text
from gateways.db.column_types import int_pk_type, created_at_type

from sqlalchemy.orm import Mapped, relationship, mapped_column
from gateways.db.models import SqlAlchemyBaseModel
from products.models import Product
from users.models import User


class OrderStatus(Enum):
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"


class Order(SqlAlchemyBaseModel):
    __table_args__ = (
        CheckConstraint(
            "(customer_email IS NOT NULL AND customer_name IS NOT NULL) OR user_id IS NOT NULL"
        ),
    )
    id: Mapped[UUID] = mapped_column(PostgresUUID, default=uuid4, primary_key=True)
    order_date: Mapped[created_at_type]
    customer_email: Mapped[str | None]
    customer_tg_username: Mapped[str]
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )
    user: Mapped[User | None] = relationship(
        back_populates="orders", lazy="joined", passive_deletes=True
    )
    customer_phone: Mapped[str | None]
    customer_name: Mapped[str | None]
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", lazy="selectin", passive_deletes=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        server_default=text(OrderStatus.PENDING.value)
    )

    @property
    def total(self) -> Decimal:
        return Decimal(sum(item.total_price for item in self.items))


class OrderItem(SqlAlchemyBaseModel):
    id: Mapped[int_pk_type]
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT")
    )
    product: Mapped[Product] = relationship(lazy="joined")
    order_id: Mapped[int] = mapped_column(ForeignKey("order.id", ondelete="CASCADE"))
    order: Mapped[Order] = relationship(back_populates="items")
    price: Mapped[Decimal]
    quantity: Mapped[int] = mapped_column(CheckConstraint("quantity > 0"))

    @property
    def total_price(self) -> Decimal:
        return self.price * self.quantity
