from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import replace
from logging import Logger
from core.services.base import BaseService
from core.uow import AbstractUnitOfWork
from sales.domain.interfaces import SalesRepositoryI
from sales.models import (
    XBOX_PARSE_REGIONS,
    PSN_PARSE_REGIONS,
    PriceUnit,
    ProductOnSale,
    ProductOnSaleCategory,
)


class AbstractPriceCalculator(ABC):
    def __post_init__(self): ...

    def __init__(self, price: PriceUnit):
        self._initial_price = price
        self.__post_init__()

    @abstractmethod
    def compute_for_region(self, region_code: str) -> PriceUnit: ...


class XboxPriceCalculator(AbstractPriceCalculator):
    def __post_init__(self):
        curr = self._initial_price.currency_code.lower()
        assert curr == "usd", f"Expected currency: usd, got: {curr}"

    def _compute_for_usa(self) -> PriceUnit:
        new_price = round(self._initial_price * 0.75, 2)
        if new_price <= 2.99:
            new_price.add_percent(70)
        elif new_price <= 4.99:
            new_price.add_percent(55)
        elif new_price <= 12.99:
            new_price.add_percent(35)
        elif new_price <= 29.99:
            new_price.add_percent(33)
        elif new_price <= 34.99:
            new_price.add_percent(31)
        elif new_price <= 39.99:
            new_price.add_percent(28)
        elif new_price <= 49.99:
            new_price.add_percent(25)
        elif new_price <= 54.99:
            new_price.add_percent(23)
        else:
            new_price.add_percent(20)
        return new_price

    def _compute_for_tr(self) -> PriceUnit:
        new_price = replace(self._initial_price)  # make a object copy
        if new_price <= 0.99:
            new_price.add_percent(200)
        elif new_price <= 1.99:
            new_price.add_percent(150)
        elif new_price <= 2.99:
            new_price.add_percent(80)
        elif new_price <= 4.99:
            new_price.add_percent(65)
        elif new_price <= 7.99:
            new_price.add_percent(55)
        elif new_price <= 9.99:
            new_price.add_percent(40)
        elif new_price <= 12.99:
            new_price.add_percent(35)
        elif new_price <= 15.99:
            new_price.add_percent(32)
        elif new_price <= 19.99:
            new_price.add_percent(28)
        elif new_price <= 24.99:
            new_price.add_percent(25)
        elif new_price <= 29.99:
            new_price.add_percent(24)
        else:
            new_price.add_percent(21)
        return new_price

    def _compute_for_ar(self) -> PriceUnit:
        addend: float
        if self._initial_price <= 0.2:
            addend = 3.4
        elif self._initial_price <= 2.0:
            addend = 5
        elif self._initial_price <= 5.0:
            addend = 7
        elif self._initial_price <= 15.0:
            addend = 10
        elif self._initial_price <= 25.0:
            addend = 12
        else:
            addend = 14
        return self._initial_price + addend

    def compute_for_region(self, region_code: str) -> PriceUnit:
        match region_code.lower():
            case XBOX_PARSE_REGIONS.US:
                return self._compute_for_usa()
            case XBOX_PARSE_REGIONS.TR:
                return self._compute_for_tr()
            case XBOX_PARSE_REGIONS.AR:
                return self._compute_for_ar()
            case _:
                raise ValueError("Unsupported region: %s" % region_code)


class PsnPriceCalculator(AbstractPriceCalculator):
    def _compute_for_ua(self) -> PriceUnit:
        assert self._initial_price.currency_code.lower() == "uah"
        return self._initial_price * 3.2

    def _compute_for_tr(self) -> PriceUnit:
        assert self._initial_price.currency_code.lower() == "tl"
        return self._initial_price * 3.2

    def compute_for_region(self, region_code: str) -> PriceUnit:
        match region_code.lower():
            case PSN_PARSE_REGIONS.UA:
                return self._compute_for_ua()
            case PSN_PARSE_REGIONS.TR:
                return self._compute_for_tr()
            case _:
                raise ValueError("Unsupported region: %s" % region_code)


class SalesService(BaseService):
    entity_name = "Product on sale"

    def __init__(
        self, uow: AbstractUnitOfWork, logger: Logger, sales_repo: SalesRepositoryI
    ) -> None:
        super().__init__(uow, logger)
        self._sales_repo = sales_repo

    async def load_new_sales(self, sales: Sequence[ProductOnSale]):
        for item in sales:
            calculator_cls: type[AbstractPriceCalculator] = (
                XboxPriceCalculator
                if item.category == ProductOnSaleCategory.XBOX
                else PsnPriceCalculator
            )
            for region, combined_price in item.prices.items():
                calculator = calculator_cls(combined_price.discounted_price)
                new_price = calculator.compute_for_region(region)
                combined_price.discounted_price = new_price
        await self._sales_repo.delete_all()
        await self._sales_repo.create_many(sales)
