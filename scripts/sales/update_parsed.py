from _base import get_redis_key_by_platform
from argparse import ArgumentParser
import asyncio


from products.domain.services import ProductsService
from gateways.db import RedisClient
from products.models import ProductPlatform
from core.ioc import get_container, Resolve
from main import ping_gateways, close_connections
from gateways.gamesparser import SalesParser


async def update_last_parsed_sales(platform: ProductPlatform, parser: SalesParser):
    redis_client = Resolve(RedisClient)
    service = Resolve(ProductsService)
    ids: list[str] = await redis_client.lrange(
        get_redis_key_by_platform(platform), 0, -1
    )
    urls = await service.get_urls_mapping([int(id) for id in ids])
    await parser.update_for_platform(platform, urls)


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
                    update_last_parsed_sales(ProductPlatform.XBOX, parser),
                    update_last_parsed_sales(ProductPlatform.PSN, parser),
                )
            case ProductPlatform.XBOX:
                await update_last_parsed_sales(ProductPlatform.XBOX, parser)
            case ProductPlatform.PSN:
                await update_last_parsed_sales(ProductPlatform.PSN, parser)
            case _:
                raise ValueError("Unsupported platform: %s" % args.platform)
    finally:
        await close_connections()


if __name__ == "__main__":
    asyncio.run(main())
