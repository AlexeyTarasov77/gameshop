from dataclasses import dataclass, field, replace
from typing import Self
from uuid import UUID, uuid4
from enum import auto
from gamesparser.models import Price as ParsedPrice, ParsedItem

from core.utils import CIEnum


class PsnParseRegions(CIEnum):
    UA = auto()
    TR = auto()


class XboxParseRegions(CIEnum):
    US = auto()
    AR = auto()
    TR = auto()


class ProductOnSaleCategory(CIEnum):
    XBOX = auto()
    PSN = auto()


class PriceUnit(ParsedPrice):
    def add_percent(self, percent: int):
        new_value = self.value + self.value / 100 * percent
        self.value = new_value

    def _get_value(self, other: float | Self) -> float:
        return other.value if isinstance(other, PriceUnit) else other

    def __add__(self, other: float | Self) -> Self:
        return replace(self, value=self.value + self._get_value(other))

    __radd__ = __add__

    def __mul__(self, other: float | Self):
        return self.__class__(
            value=self.value * self._get_value(other), currency_code=self.currency_code
        )

    __rmul__ = __mul__

    def __truediv__(self, other: float | Self):
        return self.__class__(
            value=self.value / self._get_value(other), currency_code=self.currency_code
        )

    __rtruediv__ = __truediv__

    def __sub__(self, other: float | Self):
        return self.__class__(
            value=self.value - self._get_value(other),
            currency_code=self.currency_code,
        )

    __rsub__ = __sub__

    def __le__(self, other: float | Self) -> bool:
        return self.value <= self._get_value(other)

    def __lt__(self, other: float | Self) -> bool:
        return self.value < self._get_value(other)

    def __gt__(self, other: float | Self) -> bool:
        return self.value > self._get_value(other)

    def __ge__(self, other: float | Self) -> bool:
        return self.value >= self._get_value(other)

    def __round__(self, ndigits=0) -> Self:
        return self.__class__(
            value=round(self.value, ndigits), currency_code=self.currency_code
        )


@dataclass
class RegionalPrice:
    region: str
    _base_price: PriceUnit
    _discounted_price: PriceUnit

    def __post_init__(self):
        assert (
            self.discounted_price.currency_code.lower()
            == self.base_price.currency_code.lower()
        ), "Base price and discounted price should have the same currency"

    @property
    def base_price(self):
        return self._base_price

    @base_price.setter
    def base_price(self, new_value: float | PriceUnit):
        if isinstance(new_value, PriceUnit):
            if new_value.currency_code != self._base_price.currency_code:
                self.discounted_price.currency_code = new_value.currency_code
            self._base_price = new_value
        else:
            self._base_price.value = new_value

    @property
    def discounted_price(self):
        return self._discounted_price

    @discounted_price.setter
    def discounted_price(self, new_value: float | PriceUnit):
        discount = (self.base_price - self.discounted_price).value // (
            self.base_price / 100
        ).value
        recalculated_base_price = (new_value * 100) / (100 - discount)
        self.base_price = recalculated_base_price
        if isinstance(new_value, PriceUnit):
            self._discounted_price = new_value
        else:
            self._discounted_price.value = new_value


@dataclass(kw_only=True)
class ProductOnSale(ParsedItem):
    id: UUID = field(default_factory=uuid4)
    prices: list[RegionalPrice]  # type: ignore
    category: ProductOnSaleCategory
