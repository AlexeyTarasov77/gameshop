from decimal import Decimal
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from uuid import UUID
from enum import StrEnum
from sqlalchemy import CheckConstraint, ForeignKey, text
from core.utils import LabeledEnum
from gateways.db.sqlalchemy_gateway import int_pk_type, created_at_type

from sqlalchemy.orm import Mapped, declared_attr, relationship, mapped_column
from gateways.db.sqlalchemy_gateway import SqlAlchemyBaseModel
from payments.models import PaymentMixin
from products.models import Product
from users.models import User


class OrderStatus(StrEnum):
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"


class OrderCategory(LabeledEnum):
    IN_APP = "Внутриигровая покупка"
    STEAM_TOP_UP = "Пополнение steam"
    STEAM_GIFT = "Подарок стим"


class BaseOrder(SqlAlchemyBaseModel, PaymentMixin):
    __table_args__ = (
        CheckConstraint("customer_email IS NOT NULL OR user_id IS NOT NULL"),
    )
    user = None
    total: Decimal | property = Decimal(-1)  # suborders should overwrite that
    id: Mapped[UUID] = mapped_column(PostgresUUID, default=uuid4, primary_key=True)
    order_date: Mapped[created_at_type]
    status: Mapped[OrderStatus] = mapped_column(
        server_default=text(f"'{OrderStatus.PENDING}'")
    )
    customer_email: Mapped[str | None]
    category: Mapped[OrderCategory]

    @declared_attr
    def user_id(cls):
        return mapped_column(ForeignKey("user.id", ondelete="CASCADE"))

    @property
    def client_email(self) -> str:
        email = self.customer_email
        if not email:
            # use __dict__ to prevent attempt for lazy loading
            assert "user" in self.__dict__, "Order user is not loaded"
            email = self.user.email  # type: ignore
        return email

    __mapper_args__ = {
        "polymorphic_on": "category",
    }

    def set_user(self, user: User):
        self.__dict__["user"] = user  # to prevent lazy loading when accesing attribute


class InAppOrder(BaseOrder):
    id: Mapped[UUID] = mapped_column(
        ForeignKey("base_order.id", ondelete="CASCADE"), primary_key=True
    )
    user: Mapped[User | None] = relationship(
        back_populates="in_app_orders", lazy="joined", passive_deletes=True
    )
    customer_tg_username: Mapped[str]
    customer_phone: Mapped[str | None]
    customer_name: Mapped[str | None]
    items: Mapped[list["InAppOrderItem"]] = relationship(
        back_populates="order", lazy="selectin", passive_deletes=True
    )

    @property
    def total(self) -> Decimal:
        return Decimal(sum(item.total_price for item in self.items))

    __mapper_args__ = {
        "polymorphic_identity": OrderCategory.IN_APP,
    }


class InAppOrderItem(SqlAlchemyBaseModel):
    id: Mapped[int_pk_type]
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT")
    )
    product: Mapped[Product] = relationship(lazy="joined")
    order_id: Mapped[int] = mapped_column(
        ForeignKey("in_app_order.id", ondelete="CASCADE")
    )
    order: Mapped[InAppOrder] = relationship(back_populates="items")
    price: Mapped[Decimal]
    region: Mapped[str | None]  # regions which price belongs to
    quantity: Mapped[int] = mapped_column(CheckConstraint("quantity > 0"))

    @property
    def total_price(self) -> Decimal:
        return self.price * self.quantity


class SteamTopUpOrder(BaseOrder):
    __table_args__ = (CheckConstraint("amount > 0"),)
    id: Mapped[UUID] = mapped_column(
        ForeignKey("base_order.id", ondelete="CASCADE"), primary_key=True
    )
    steam_login: Mapped[str]
    amount: Mapped[Decimal]
    percent_fee: Mapped[int]
    user: Mapped[User | None] = relationship(
        back_populates="steam_top_up_orders", lazy="joined", passive_deletes=True
    )

    @property
    def total(self) -> Decimal:
        return self.amount + self.amount / 100 * self.percent_fee

    __mapper_args__ = {
        "polymorphic_identity": OrderCategory.STEAM_TOP_UP,
    }


class SteamGiftOrder(BaseOrder):
    id: Mapped[UUID] = mapped_column(
        ForeignKey("base_order.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT")
    )
    region: Mapped[str]
    product: Mapped[Product] = relationship(lazy="joined")
    total: Mapped[Decimal]  # type: ignore
    user: Mapped[User | None] = relationship(
        back_populates="steam_gift_orders", lazy="joined", passive_deletes=True
    )
    friend_link: Mapped[str]

    __mapper_args__ = {
        "polymorphic_identity": OrderCategory.STEAM_GIFT,
    }
