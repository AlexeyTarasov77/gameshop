from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.dialects.postgresql import ENUM

from gateways.db.sqlalchemy_gateway import created_at_type, int_pk_type, updated_at_type
from gateways.db.sqlalchemy_gateway import SqlAlchemyBaseModel
from sqlalchemy import CHAR, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enum import Enum, auto

from core.utils import CIEnum


class LabeledID(int):
    def __new__(cls, value: int, *args, **kwargs):
        if value <= 0:
            raise ValueError("id should be > 0")
        return super().__new__(cls, value)

    #
    def __init__(self, value: int, label: str) -> None:
        super().__init__()
        self.label = label

    def __str__(self):
        return self.label


class _BaseLabeledEnum(Enum):
    @classmethod
    def _missing_(cls, value: Any):
        try:
            if not isinstance(value, str):
                raise ValueError()
            # case-insensitive lookup in members first, then try to convert to int and find in values
            found = cls.__members__.get(value.upper()) or (
                int(value) in [member.value for member in cls.__members__.values()]
                and cls(int(value))
            )
            if not found:
                return None
            return found
        except ValueError:
            # value is not str or failed to convert to integer
            return None


class ProductPlatform(_BaseLabeledEnum):
    XBOX = LabeledID(1, "xbox")
    PSN = LabeledID(2, "psn")
    STEAM = LabeledID(3, "steam")


class ProductCategory(_BaseLabeledEnum):
    GAMES = LabeledID(1, "Игры")
    SUBSCRIPTIONS = LabeledID(2, "Подписки")
    RECHARGE_CARDS = LabeledID(3, "Карты пополнения")
    DONATE = LabeledID(4, "Внутриигровая валюта")
    XBOX_SALES = LabeledID(5, "Распродажа XBOX")
    PSN_SALES = LabeledID(6, "Распродажа PSN")
    STEAM_KEYS = LabeledID(7, "Ключи Steam")


class ProductDeliveryMethod(_BaseLabeledEnum):
    KEY = LabeledID(1, "Ключ")
    ACCOUNT_PURCHASE = LabeledID(2, "Покупка на аккаунт")
    GIFT = LabeledID(3, "Передача подарком")


class PsnParseRegions(CIEnum):
    UA = auto()
    TR = auto()


class XboxParseRegions(CIEnum):
    US = auto()
    AR = auto()
    TR = auto()


class Product(SqlAlchemyBaseModel):
    __table_args__ = (UniqueConstraint("name", "category", "platform"),)

    id: Mapped[int_pk_type]
    name: Mapped[str]
    description: Mapped[str] = mapped_column(server_default="")
    category: Mapped[ProductCategory] = mapped_column(ENUM(ProductCategory))
    delivery_method: Mapped[ProductDeliveryMethod] = mapped_column(
        ENUM(ProductDeliveryMethod)
    )
    platform: Mapped[ProductPlatform] = mapped_column(ENUM(ProductPlatform))
    image_url: Mapped[str]
    in_stock: Mapped[bool] = mapped_column(server_default=text("true"))
    discount: Mapped[int] = mapped_column(server_default=text("0"))
    with_gp: Mapped[
        bool | None
    ]  # indicates whether discount applies to game pass (only for xbox sales)
    deal_until: Mapped[datetime | None]
    prices: Mapped[list["RegionalPrice"]] = relationship(
        back_populates="product", lazy="selectin"
    )
    created_at: Mapped[created_at_type]
    updated_at: Mapped[updated_at_type]

    @property
    def total_discount(self) -> int:
        discount = self.discount
        if self.deal_until and (datetime.now() >= self.deal_until):
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
        CHAR(3), primary_key=True, server_default=text("")
    )
    converted_from_curr: Mapped[str | None] = mapped_column(CHAR(3))

    @property
    def total_price(self) -> Decimal:
        total = self.base_price - (
            Decimal(self.product.total_discount / 100) * self.base_price
        )
        return total.quantize(Decimal("0.01"), ROUND_HALF_UP)

    def calc_discounted_price(self, discount: int):
        self.discounted_price = self.base_price - self.base_price / 100 * discount
        return self.discounted_price
