from collections.abc import Sequence
from dataclasses import asdict
from logging import Logger
import time
import asyncio
import sys
from httpx import AsyncClient
from core.ioc import Resolve
from gamesparser import ParsedItem, PsnParser, XboxParser

from sales.domain.services import SalesService
from sales.models import (
    PSN_PARSE_REGIONS,
    XBOX_PARSE_REGIONS,
    CombinedPrice,
    PriceUnit,
    ProductOnSale,
    ProductOnSaleCategory,
)


def parsed_to_domain_model(
    item: ParsedItem, category: ProductOnSaleCategory
) -> ProductOnSale:
    casted_prices = {}
    for region, price in item.prices.items():
        casted_prices[region] = CombinedPrice(
            PriceUnit(**asdict(price.base_price)),
            PriceUnit(**asdict(price.discounted_price)),
        )

    return ProductOnSale(
        **asdict(item),
        category=category,
        prices=casted_prices,
    )


async def load_parsed(
    psn_sales: Sequence[ParsedItem], xbox_sales: Sequence[ParsedItem]
):
    sales: list[ProductOnSale] = []
    for product in psn_sales:
        sales.append(parsed_to_domain_model(product, ProductOnSaleCategory.PSN))
    for product in xbox_sales:
        sales.append(parsed_to_domain_model(product, ProductOnSaleCategory.XBOX))
    service = Resolve(SalesService)
    await service.load_sales(sales)


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
    await load_parsed(psn_sales, xbox_sales)
    logger.info("Sales succesfully loaded")


if __name__ == "__main__":
    asyncio.run(main())
