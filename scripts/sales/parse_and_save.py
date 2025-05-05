from _base import (
    get_redis_key_by_platform,
    update_sales_details,
    save_unprocessed_ids,
)
from collections.abc import Sequence

import asyncio
from argparse import ArgumentParser

from main import ping_gateways, close_connections
from products.models import ProductPlatform
from core.ioc import get_container
from gateways.gamesparser import SalesParser


async def update_sales_wrapper(
    inserted_ids: Sequence[int], platform: ProductPlatform, parser: SalesParser
):
    key = get_redis_key_by_platform(platform)
    await save_unprocessed_ids(key, inserted_ids)
    await update_sales_details(inserted_ids, platform, parser)


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
                limit_per_parser = args.limit // 2 if args.limit else None
                xbox_ids, psn_ids = await asyncio.gather(
                    parser.parse_and_save_xbox(limit_per_parser),
                    parser.parse_and_save_psn(limit_per_parser),
                )
                await asyncio.gather(
                    update_sales_wrapper(
                        xbox_ids,
                        ProductPlatform.XBOX,
                        parser,
                    ),
                    update_sales_wrapper(
                        psn_ids,
                        ProductPlatform.PSN,
                        parser,
                    ),
                )
            case ProductPlatform.XBOX:
                inserted_ids = await parser.parse_and_save_xbox(args.limit)
                await update_sales_wrapper(inserted_ids, ProductPlatform.XBOX, parser)
            case ProductPlatform.PSN:
                inserted_ids = await parser.parse_and_save_psn(args.limit)
                await update_sales_wrapper(inserted_ids, ProductPlatform.PSN, parser)
            case _:
                raise ValueError("Unsupported platform: %s" % args.platform)
    finally:
        await close_connections()


if __name__ == "__main__":
    asyncio.run(main())
