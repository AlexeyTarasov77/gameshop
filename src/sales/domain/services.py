from collections.abc import Sequence
from logging import Logger
from core.services.base import BaseService
from core.uow import AbstractUnitOfWork
from sales.models import XBOX_PARSE_REGIONS, PriceUnit, ProductOnSale


class XboxPriceCalculator:
    def __init__(self, price: PriceUnit):
        assert price.currency_code.lower() == "usd", "expected usd currency"
        self._initial_price = price

    def _compute_for_usa(self) -> PriceUnit:
        new_price = self._initial_price * 0.75
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
        new_price = self._initial_price * 0.75
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

    def compute_for_region(self, region_code: str) -> PriceUnit:
        match region_code.lower():
            case XBOX_PARSE_REGIONS.US:
                return self._compute_for_usa()
            case XBOX_PARSE_REGIONS.TR:
                return self._compute_for_tr()
            case _:
                raise ValueError("Unsupported region: %s" % region_code)


class SalesService(BaseService):
    def __init__(self, uow: AbstractUnitOfWork, logger: Logger) -> None:
        super().__init__(uow, logger)

    async def load_sales(self, sales: Sequence[ProductOnSale]): ...
