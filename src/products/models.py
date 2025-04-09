from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from pytz import UTC

from core.schemas import EMPTY_REGION
from core.utils.enums import IntWithLabel
from gateways.db.sqlalchemy_gateway import (
    int_pk_type,
    timestamptz,
    SqlAlchemyBaseModel,
    TimestampMixin,
)
from sqlalchemy import CHAR, CheckConstraint, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from random import randint
from enum import Enum, auto

from core.utils import CIEnum, LabeledEnum


class ProductPlatform(LabeledEnum):
    XBOX = "xbox"
    PSN = "psn"
    STEAM = "steam"


class SalesCategories(Enum):
    XBOX_SALES = IntWithLabel(randint(10, 100), "Распродажи xbox")
    PSN_SALES = IntWithLabel(randint(10, 100), "Распродажи psn")


class ProductCategory(LabeledEnum):
    GAMES = "Игры"
    SUBSCRIPTIONS = "Подписки"
    RECHARGE_CARDS = "Карты пополнения"
    DONATE = "Внутриигровая валюта"
    STEAM_TOPUP = "Пополнение Steam"


class ProductDeliveryMethod(LabeledEnum):
    KEY = "Ключ"
    ACCOUNT_PURCHASE = "Покупка на аккаунт"
    NEW_ACCOUNT_PURCHASE = "Покупка на новый аккаунт"
    GIFT = "gift"


class PsnParseRegions(CIEnum):
    UA = auto()
    TR = auto()


class XboxParseRegions(CIEnum):
    US = auto()
    AR = auto()
    TR = auto()


class Product(SqlAlchemyBaseModel, TimestampMixin):
    unique_fields = ("name", "category", "platform")
    __table_args__ = (
        UniqueConstraint(*unique_fields),
        CheckConstraint(
            text(
                "(platform = 'STEAM' AND category = 'GAMES' AND sub_id IS NOT NULL) OR (platform != 'STEAM' OR category != 'GAMES' AND sub_id IS NULL)"
            )
        ),
    )

    id: Mapped[int_pk_type]
    name: Mapped[str]
    description: Mapped[str] = mapped_column(server_default="")
    category: Mapped[ProductCategory]
    platform: Mapped[ProductPlatform]
    delivery_method: Mapped[ProductDeliveryMethod]
    image_url: Mapped[str]
    in_stock: Mapped[bool] = mapped_column(server_default=text("true"))
    discount: Mapped[int] = mapped_column(server_default=text("0"))
    with_gp: Mapped[
        bool | None
    ]  # indicates whether discount applies to game pass (only for xbox sales)
    deal_until: Mapped[timestamptz | None]
    prices: Mapped[list["RegionalPrice"]] = relationship(
        back_populates="product", lazy="selectin"
    )
    sub_id: Mapped[int | None]

    @property
    def is_discount_expired(self) -> bool:
        if self.deal_until and (
            datetime.now(UTC) >= self.deal_until.replace(tzinfo=UTC)
        ):
            return True
        return False

    @property
    def total_discount(self) -> int:
        discount = self.discount
        if self.is_discount_expired:
            discount = 0
        return discount


class RegionalPrice(SqlAlchemyBaseModel):
    __allow_unmapped__ = True
    discounted_price: Decimal  # calculated dynamically from base_price and discount

    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"), primary_key=True
    )
    product: Mapped[Product] = relationship(back_populates="prices")
    base_price: Mapped[Decimal]  # price in rub
    # use empty string instead of nullable field to create primary key on that field
    region_code: Mapped[str] = mapped_column(
        CHAR(3), primary_key=True, server_default=text(EMPTY_REGION)
    )
    original_curr: Mapped[str | None] = mapped_column(CHAR(3))

    @property
    def total_price(self) -> Decimal:
        total = self.base_price - (
            Decimal(self.product.total_discount / 100) * self.base_price
        )
        return total.quantize(Decimal("0.01"), ROUND_HALF_UP)

    def calc_discounted_price(self, discount: int):
        self.discounted_price = self.base_price - self.base_price / 100 * discount
        return self.discounted_price
