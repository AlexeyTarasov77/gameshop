from collections.abc import Sequence
from logging import Logger
import os

import asyncio
import sys
from pathlib import Path
from argparse import ArgumentParser


sys.path.append((Path().parent.parent / "src").absolute().as_posix())

from config import ConfigMode

if not os.environ.get("MODE"):
    os.environ["MODE"] = ConfigMode.LOCAL

from products.domain.services import ProductsService
from gateways.db import RedisClient
from main import ping_gateways, close_connections
from products.models import ProductPlatform
from core.ioc import Resolve, get_container
from gateways.gamesparser import SalesParser

XBOX_REDIS_KEY = "parsed_xbox"
PSN_REDIS_KEY = "parsed_psn"


async def save_inserted_ids(key: str, ids: Sequence[int]):
    """
    Saves ids of most recently parsed and saved sales
    which could be retrieved for further processing
    """
    redis_client = Resolve(RedisClient)
    logger = Resolve(Logger)
    await redis_client.delete(key)
    if not ids:
        logger.info("Nothing to save in redis. Exiting")
        return
    await redis_client.lpush(key, *ids)
    logger.info("Succesfully saved %s lastly inserted ids", len(ids))


async def update_sales_details(
    inserted_ids: Sequence[int], platform: ProductPlatform, parser: SalesParser
):
    service = Resolve(ProductsService)
    urls_mapping = await service.get_urls_mapping(inserted_ids)
    match platform:
        case ProductPlatform.PSN:
            await save_inserted_ids(PSN_REDIS_KEY, inserted_ids)
            await parser.update_psn_details(urls_mapping, timeout=1)
        case ProductPlatform.XBOX:
            await save_inserted_ids(XBOX_REDIS_KEY, inserted_ids)
            await parser.update_xbox_details(urls_mapping)
        case _:
            raise ValueError("Unsupported platform: %s" % platform)


async def main():
    await ping_gateways()
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-l", "--limit", type=int)
    arg_parser.add_argument("-p", "--platform", type=ProductPlatform)
    args = arg_parser.parse_args()
    parser: SalesParser = get_container().instantiate(SalesParser)
    try:
        match args.platform:
            case None:
                limit_per_parser = args.limit // 2
                xbox_ids, psn_ids = await asyncio.gather(
                    parser.parse_and_save_xbox(limit_per_parser),
                    parser.parse_and_save_psn(limit_per_parser),
                )
                await asyncio.gather(
                    update_sales_details(
                        xbox_ids,
                        ProductPlatform.XBOX,
                        parser,
                    ),
                    update_sales_details(
                        psn_ids,
                        ProductPlatform.PSN,
                        parser,
                    ),
                )
            case ProductPlatform.XBOX:
                inserted_ids = await parser.parse_and_save_xbox(args.limit)
                await update_sales_details(inserted_ids, ProductPlatform.XBOX, parser)
            case ProductPlatform.PSN:
                inserted_ids = await parser.parse_and_save_psn(args.limit)
                await update_sales_details(inserted_ids, ProductPlatform.PSN, parser)
            case _:
                raise ValueError("Unsupported platform: %s" % args.platform)
    finally:
        await close_connections()


if __name__ == "__main__":
    asyncio.run(main())
