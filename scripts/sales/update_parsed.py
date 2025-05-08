from collections.abc import Sequence
from _base import get_redis_key_by_platform, update_sales_details
from argparse import ArgumentParser
import asyncio


from core.tasks import BackgroundJobs
from gateways.db import RedisClient
from products.models import ProductPlatform
from core.ioc import get_container, Resolve
from main import ping_gateways, close_connections
from gateways.gamesparser import SalesParser


async def update_last_parsed_sales(
    platform: ProductPlatform, parser: SalesParser
) -> bool:
    redis_client = Resolve(RedisClient)
    ids: list[str] = await redis_client.lrange(
        get_redis_key_by_platform(platform), 0, -1
    )
    if not ids:
        return False
    await update_sales_details([int(id) for id in ids], platform, parser)
    return True


async def check_has_something_for_update(platforms: Sequence[ProductPlatform]) -> bool:
    redis_client = Resolve(RedisClient)
    coros = [
        redis_client.llen(get_redis_key_by_platform(platform)) for platform in platforms
    ]
    res = await asyncio.gather(*coros)
    return any(res)


async def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-p", "--platform", type=ProductPlatform)
    args = arg_parser.parse_args()
    has_something_for_update = await check_has_something_for_update(
        [ProductPlatform.XBOX, ProductPlatform.PSN]
        if args.platform is None
        else [args.platform]
    )
    if not has_something_for_update:
        print("Nothing to update!")
        await close_connections()
        return
    await ping_gateways()
    parser: SalesParser = get_container().instantiate(SalesParser)
    bg_jobs = Resolve(BackgroundJobs)
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
        await bg_jobs.remove_products_from_sale(exit_after_update=True)
    finally:
        await close_connections()


if __name__ == "__main__":
    asyncio.run(main())
