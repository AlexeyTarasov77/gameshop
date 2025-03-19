from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from gateways.db.sqlalchemy_gateway import int_pk_type
from gateways.db.sqlalchemy_gateway import SqlAlchemyBaseModel, TimestampMixin
from sqlalchemy import CHAR, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enum import Enum, auto

from core.utils import CIEnum


class LabeledID(int):
    def __new__(cls, value: int, *args, **kwargs):
        if value <= 0:
            raise ValueError("id should be > 0")
        return super().__new__(cls, value)

    def __init__(self, _, label: str) -> None:
        super().__init__()
        self.label = label

    def __str__(self):
        return self.label


class _BaseLabeledEnum(Enum):
    def __new__(cls, value: str):
        cls._next_id = getattr(cls, "_next_id", 0) + 1
        obj = object.__new__(cls)
        obj._value_ = LabeledID(cls._next_id, value)
        return obj

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
    XBOX = "xbox"
    PSN = "psn"
    STEAM = "steam"


class ProductCategory(_BaseLabeledEnum):
    GAMES = "Игры"
    SUBSCRIPTIONS = "Подписки"
    RECHARGE_CARDS = "Карты пополнения"
    DONATE = "Внутриигровая валюта"
    XBOX_SALES = "Распродажа XBOX"
    PSN_SALES = "Распродажа PSN"
    STEAM_KEYS = "Ключи Steam"


class ProductDeliveryMethod(_BaseLabeledEnum):
    KEY = "Ключ"
    ACCOUNT_PURCHASE = "Покупка на аккаунт"
    NEW_ACCOUNT_PURCHASE = "Покупка на новый аккаунт"
    GIFT = "Передача подарком"


class PsnParseRegions(CIEnum):
    UA = auto()
    TR = auto()


class XboxParseRegions(CIEnum):
    US = auto()
    AR = auto()
    TR = auto()


class Product(SqlAlchemyBaseModel, TimestampMixin):
    __table_args__ = (UniqueConstraint("name", "category", "platform"),)

    id: Mapped[int_pk_type]
    name: Mapped[str]
    description: Mapped[str] = mapped_column(server_default="")
    category: Mapped[ProductCategory]
    platform: Mapped[ProductPlatform]
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

    @property
    def delivery_methods(self) -> list[ProductDeliveryMethod]:
        """Chooses delivery_methods based on product platform and price regions"""
        match self.platform:
            case ProductPlatform.PSN:
                return [ProductDeliveryMethod.ACCOUNT_PURCHASE]
            case ProductPlatform.STEAM:
                return [ProductDeliveryMethod.KEY, ProductDeliveryMethod.GIFT]
            case ProductPlatform.XBOX:
                regions = [price.region_code.lower().strip() for price in self.prices]
                assert len(regions) > 0
                if XboxParseRegions.US in regions:
                    methods = [ProductDeliveryMethod.KEY]
                    if len(regions) > 1:  # if something except of us
                        methods.append(ProductDeliveryMethod.NEW_ACCOUNT_PURCHASE)
                    return methods
                return [ProductDeliveryMethod.NEW_ACCOUNT_PURCHASE]

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
