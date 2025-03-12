from collections.abc import Sequence
from dataclasses import asdict
from logging import Logger
import time
import asyncio
import sys
from pathlib import Path

sys.path.append((Path() / "src").absolute().as_posix())

from products.domain.services import ProductsService
from products.models import ProductPlatform
from products.schemas import ProductForLoadDTO

from gateways.db import RedisClient
from httpx import AsyncClient
from core.ioc import Resolve
from gamesparser import ParsedItem, PsnParser, XboxParser

from sales.models import (
    PsnParseRegions,
    XboxParseRegions,
)


def parsed_to_dto(product: ParsedItem, platform: ProductPlatform) -> ProductForLoadDTO:
    return ProductForLoadDTO.model_validate(
        {
            **asdict(product),
            "platform": platform,
            "prices": {k: v.base_price for k, v in product.prices.items()},
        }
    )


async def load_parsed(
    psn_sales: Sequence[ParsedItem], xbox_sales: Sequence[ParsedItem]
):
    try:
        sales: list[ProductForLoadDTO] = []
        for product in psn_sales:
            sales.append(parsed_to_dto(product, ProductPlatform.PSN))
        for product in xbox_sales:
            sales.append(parsed_to_dto(product, ProductPlatform.XBOX))
        service = Resolve(ProductsService)
        await service.load_new_sales(sales)
    finally:
        await Resolve(RedisClient).aclose()  # type: ignore


async def main():
    logger = Resolve(Logger)
    client = Resolve(AsyncClient)
    try:
        try:
            limit = int(sys.argv[1])
        except Exception:
            limit = None
        logger.info("Start parsing up to %s sales...", limit)
        psn_parser = PsnParser([el.value for el in PsnParseRegions], client, limit)
        xbox_parser = XboxParser([el.value for el in XboxParseRegions], client, limit)
        t1 = time.perf_counter()
        psn_sales, xbox_sales = await asyncio.gather(
            psn_parser.parse(), xbox_parser.parse()
        )
        logger.info(
            "%s sales succesfully parsed, which took: %s seconds",
            len(psn_sales) + len(xbox_sales),
            round(time.perf_counter() - t1, 1),
        )
        logger.info("Loading sales to db...")
        await load_parsed(psn_sales, xbox_sales)
        logger.info("Sales succesfully loaded")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
