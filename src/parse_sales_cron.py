from collections.abc import Sequence
from logging import Logger
import time
import asyncio
import sys
from httpx import AsyncClient
from redis.asyncio import Redis
from core.ioc import Resolve
from gamesparser import ParsedItem, PsnParser, XboxParser

from products.models import ProductOnSaleCategory


async def load_to_db(psn_sales: Sequence[ParsedItem], xbox_sales: Sequence[ParsedItem]):
    redis_conn = Resolve(Redis)
    key = "sales"
    await redis_conn.json().set(key, "$", [])
    psn_data = [
        {**item.as_json_serializable(), "category": ProductOnSaleCategory.PSN}
        for item in psn_sales
    ]
    xbox_data = [
        {**item.as_json_serializable(), "category": ProductOnSaleCategory.XBOX}
        for item in xbox_sales
    ]
    await redis_conn.json().arrappend(key, "$", *(psn_data + xbox_data))  # type: ignore


async def main():
    logger = Resolve(Logger)
    try:
        limit = int(sys.argv[1])
    except Exception:
        limit = None
    async with AsyncClient() as client:
        logger.info("Start parsing up to %s sales...", limit)
        psn_parser = PsnParser(("ua", "tr"), client, limit)
        xbox_parser = XboxParser(("us", "ar", "tr"), client, limit)
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
