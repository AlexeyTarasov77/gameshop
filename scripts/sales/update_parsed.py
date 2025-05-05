from argparse import ArgumentParser
import sys
import os
import asyncio
from pathlib import Path


sys.path.append((Path().parent.parent / "src").absolute().as_posix())

from config import ConfigMode

if not os.environ.get("MODE"):
    os.environ["MODE"] = ConfigMode.LOCAL

from products.domain.interfaces import ParsedUrlsMapping
from products.domain.services import ProductsService
from parse_and_save import PSN_REDIS_KEY, XBOX_REDIS_KEY
from gateways.db import RedisClient
from products.models import ProductPlatform
from core.ioc import get_container, Resolve
from main import ping_gateways, close_connections
from gateways.gamesparser import SalesParser


async def retrieve_parsed_urls(key: str) -> ParsedUrlsMapping:
    redis_client = Resolve(RedisClient)
    service = Resolve(ProductsService)
    ids: list[str] = await redis_client.lrange(key, 0, -1)
    return await service.get_urls_mapping([int(id) for id in ids])


async def update_parsed_sales(platform: ProductPlatform, parser: SalesParser):
    match platform:
        case ProductPlatform.PSN:
            urls = await retrieve_parsed_urls(PSN_REDIS_KEY)
            await parser.update_psn_details(
                urls,
                timeout=1,
            )
        case ProductPlatform.XBOX:
            urls = await retrieve_parsed_urls(XBOX_REDIS_KEY)
            await parser.update_xbox_details(urls)


async def main():
    await ping_gateways()
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-p", "--platform", type=ProductPlatform)
    args = arg_parser.parse_args()
    parser: SalesParser = get_container().instantiate(SalesParser)
    try:
        match args.platform:
            case None:
                await asyncio.gather(
                    update_parsed_sales(ProductPlatform.XBOX, parser),
                    update_parsed_sales(ProductPlatform.PSN, parser),
                )
            case ProductPlatform.XBOX:
                await update_parsed_sales(ProductPlatform.XBOX, parser)
            case ProductPlatform.PSN:
                await update_parsed_sales(ProductPlatform.PSN, parser)
            case _:
                raise ValueError("Unsupported platform: %s" % args.platform)
    finally:
        await close_connections()


if __name__ == "__main__":
    asyncio.run(main())
