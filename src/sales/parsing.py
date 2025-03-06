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
