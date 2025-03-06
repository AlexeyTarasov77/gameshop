from collections.abc import Sequence
from decimal import Decimal
from copy import copy
from enum import StrEnum, auto
from logging import Logger
import time
import asyncio
import sys
from gamesparser.models import ParsedPriceByRegion, Price
from httpx import AsyncClient
from redis.asyncio import Redis
from core.ioc import Resolve
from gamesparser import ParsedItem, PsnParser, XboxParser

from sales.models import ProductOnSaleCategory


class PSN_PARSE_REGIONS(StrEnum):
    UA = auto()
    TR = auto()


class XBOX_PARSE_REGIONS(StrEnum):
    US = auto()
    AR = auto()
    TR = auto()


def check_price_currency(regional_price: ParsedPriceByRegion, currency: str):
    base_price_curr = regional_price.base_price.currency_code.lower()
    discounted_price_curr = regional_price.discounted_price.currency_code.lower()
    expected = currency.lower()
    err_msg = f"Unknown currency: %s. Expected: {expected}"
    assert base_price_curr == expected, err_msg % base_price_curr
    assert discounted_price_curr == expected, err_msg % discounted_price_curr


def _add_percent(value: Decimal, percent: int):
    return value + value / Decimal(100) * percent


def _recalc_base_price(discounted_price: Price, discount: int) -> Price:
    base_price_value = round((discounted_price.value * 100) / (100 - discount), 2)
    base_price = Price(
        value=base_price_value, currency_code=discounted_price.currency_code
    )
    return base_price


class XboxPriceCalculator:
    def __init__(self, price: Price):
        assert price.currency_code.lower() == "usd", "expected usd currency"
        self._initial_price = price

    def _compute_for_usa(self) -> Price:
        value = Decimal(self._initial_price.value) * Decimal(0.75)
        if value <= Decimal(2.99):
            value = _add_percent(value, 70)
        elif value <= Decimal(4.99):
            value = _add_percent(value, 55)
        elif value <= Decimal(12.99):
            value = _add_percent(value, 35)
        elif value <= Decimal(29.99):
            value = _add_percent(value, 33)
        elif value <= Decimal(34.99):
            value = _add_percent(value, 31)
        elif value <= Decimal(39.99):
            value = _add_percent(value, 28)
        elif value <= Decimal(49.99):
            value = _add_percent(value, 25)
        elif value <= Decimal(54.99):
            value = _add_percent(value, 23)
        else:
            value = _add_percent(value, 20)
        new_price = copy(self._initial_price)
        new_price.value = float(value)
        return new_price

    def _compute_for_tr(self) -> Price:
        value = Decimal(self._initial_price.value)
        if value <= Decimal(0.99):
            value = _add_percent(value, 200)
        elif value <= Decimal(1.99):
            value = _add_percent(value, 150)
        elif value <= Decimal(2.99):
            value = _add_percent(value, 80)
        elif value <= Decimal(4.99):
            value = _add_percent(value, 65)
        elif value <= Decimal(7.99):
            value = _add_percent(value, 55)
        elif value <= Decimal(9.99):
            value = _add_percent(value, 40)
        elif value <= Decimal(12.99):
            value = _add_percent(value, 35)
        elif value <= Decimal(15.99):
            value = _add_percent(value, 32)
        elif value <= Decimal(19.99):
            value = _add_percent(value, 28)
        elif value <= Decimal(24.99):
            value = _add_percent(value, 25)
        elif value <= Decimal(29.99):
            value = _add_percent(value, 24)
        else:
            value = _add_percent(value, 21)
        new_price = copy(self._initial_price)
        new_price.value = float(value)
        return new_price

    def compute_for_region(self, region_code: str) -> Price:
        match region_code.lower():
            case XBOX_PARSE_REGIONS.US:
                return self._compute_for_usa()
            case XBOX_PARSE_REGIONS.TR:
                return self._compute_for_tr()
            case _:
                raise ValueError("Unsupported region: %s" % region_code)


async def load_to_db(psn_sales: Sequence[ParsedItem], xbox_sales: Sequence[ParsedItem]):
    redis_conn = Resolve(Redis)
    key = "sales"
    await redis_conn.json().set(key, "$", [])
    psn_data = []
    for item in psn_sales:
        data = {**item.as_json_serializable(), "category": ProductOnSaleCategory.PSN}
        # compute new price
        psn_data.append(data)

    xbox_data = []
    for item in xbox_sales:
        for region_code, regional_price in item.prices.items():
            check_price_currency(regional_price, "usd")
            calculator = XboxPriceCalculator(regional_price.discounted_price)
            new_price = calculator.compute_for_region(region_code)
            item.prices[region_code].discounted_price = new_price
            item.prices[region_code].base_price = _recalc_base_price(
                new_price, item.discount
            )
        data = item.as_json_serializable()
        data["category"] = ProductOnSaleCategory.XBOX
        xbox_data.append(data)

    await redis_conn.json().arrappend(key, "$", *(psn_data + xbox_data))  # type: ignore


async def main():
    logger = Resolve(Logger)
    try:
        limit = int(sys.argv[1])
    except Exception:
        limit = None
    async with AsyncClient() as client:
        logger.info("Start parsing up to %s sales...", limit)
        psn_parser = PsnParser([el.value for el in PSN_PARSE_REGIONS], client, limit)
        xbox_parser = XboxParser([el.value for el in XBOX_PARSE_REGIONS], client, limit)
        t1 = time.perf_counter()
        psn_sales, xbox_sales = await asyncio.gather(
            xbox_parser.parse(), psn_parser.parse()
        )
        logger.info(
            "%s sales succesfully parsed, which took: %s seconds",
            len(psn_sales) + len(xbox_sales),
            round(time.perf_counter() - t1, 1),
        )
    logger.info("Loading sales to db...")
    await load_to_db(psn_sales, xbox_sales)
    logger.info("Sales succesfully loaded")


if __name__ == "__main__":
    asyncio.run(main())
