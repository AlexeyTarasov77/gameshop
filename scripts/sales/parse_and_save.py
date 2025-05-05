from _base import UPDATE_CHUNK_SIZE, get_redis_key_by_platform
from collections.abc import Sequence
from logging import Logger

import asyncio
from argparse import ArgumentParser


from products.domain.services import ProductsService
from core.utils import chunkify
from gateways.db import RedisClient
from main import ping_gateways, close_connections
from products.models import ProductPlatform
from core.ioc import Resolve, get_container
from gateways.gamesparser import SalesParser


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
    logger.info("Succesfully saved %s lastly inserted ids under key: %s", len(ids), key)


async def update_sales_details(
    inserted_ids: Sequence[int], platform: ProductPlatform, parser: SalesParser
):
    service = Resolve(ProductsService)
    urls_mapping = await service.get_urls_mapping(inserted_ids)
    ids = list(urls_mapping.keys())
    key = get_redis_key_by_platform(platform)
    await save_inserted_ids(key, inserted_ids)
    for i, chunk in enumerate(
        chunkify(list(urls_mapping.items()), UPDATE_CHUNK_SIZE), 1
    ):
        urls_mapping_chunk = dict(chunk)
        await parser.update_for_platform(platform, urls_mapping_chunk)
        await save_inserted_ids(key, ids[len(urls_mapping_chunk) * i :])


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
