from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.dialects.postgresql import ENUM

from gateways.db.sqlalchemy_gateway import created_at_type, int_pk_type, updated_at_type
from gateways.db.sqlalchemy_gateway import SqlAlchemyBaseModel
from sqlalchemy import CHAR, ForeignKey, UniqueConstraint, text
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enum import auto

from core.utils import CIEnum


class ProductPlatform(CIEnum):
    XBOX = auto()
    PSN = auto()


class ProductCategory(CIEnum):
    GAMES = "Игры"
    SUBSCRIPTIONS = "Подписки"
    RECHARGE_CARDS = "Карты пополнения"
    DONATE = "Внутриигровая валюта"
    XBOX_SALES = "Распродажа XBOX"
    PSN_SALES = "Распродажа PSN"
    STEAM_KEYS = "Ключи Steam"


class ProductDeliveryMethod(CIEnum):
    KEY = "Ключ"
    ACCOUNT_PURCHASE = "Покупка на аккаунт"
    GIFT = "Передача подарком"


class PsnParseRegions(CIEnum):
    UA = auto()
    TR = auto()


class XboxParseRegions(CIEnum):
    US = auto()
    AR = auto()
    TR = auto()

    # @discounted_price.setter
    # def discounted_price(self, new_value: float | PriceUnit):
    #     discount = (self.base_price - self.discounted_price).value // (
    #         self.base_price / 100
    #     ).value
    #     recalculated_base_price = (new_value * 100) / (100 - discount)
    #     self.base_price = recalculated_base_price
    #     if isinstance(new_value, PriceUnit):
    #         self._discounted_price = new_value
    #     else:
    #         self._discounted_price.value = new_value
    #


class Product(SqlAlchemyBaseModel):
    __table_args__ = (UniqueConstraint("name", "category", "platform"),)

    id: Mapped[int_pk_type]
    name: Mapped[str]
    description: Mapped[str] = mapped_column(server_default="")
    # category_id: Mapped[int] = mapped_column(
    #     ForeignKey("category.id", ondelete="CASCADE")
    # )
    # platform_id: Mapped[int] = mapped_column(
    #     ForeignKey("platform.id", ondelete="CASCADE")
    # )
    # delivery_method_id: Mapped[int] = mapped_column(
    #     ForeignKey("delivery_method.id", ondelete="CASCADE")
    # )
    # category: Mapped["Category"] = relationship(
    #     back_populates="products", lazy="joined"
    # )
    # platform: Mapped["Platform"] = relationship(
    #     back_populates="products", lazy="joined"
    # )
    # delivery_method: Mapped["DeliveryMethod"] = relationship(
    #     back_populates="products", lazy="joined"
    # )
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


class BaseRefModel(SqlAlchemyBaseModel):
    __abstract__ = True
    id: Mapped[int_pk_type]
    name: Mapped[str]
    url: Mapped[str] = mapped_column(unique=True)

    # @declared_attr
    # def products(self):
    #     return relationship(Product, back_populates=self.__tablename__)


class Category(BaseRefModel): ...


class Platform(BaseRefModel): ...


class DeliveryMethod(BaseRefModel): ...
