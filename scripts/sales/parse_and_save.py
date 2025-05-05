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

from gateways.db import RedisClient
from products.domain.interfaces import SavedGameInfo
from main import ping_gateways, close_connections
from products.models import ProductPlatform
from core.ioc import Resolve, get_container
from gateways.gamesparser import SalesParser

XBOX_REDIS_KEY = "parsed_xbox"
PSN_REDIS_KEY = "parsed_psn"


async def save_parsed_urls(
    redis_client: RedisClient, key: str, urls: Sequence[SavedGameInfo]
):
    """Saves most recently parsed and saved sequence of url+id"""
    logger = Resolve(Logger)
    await redis_client.delete(key)
    if not urls:
        logger.info("Nothing to save in redis. Exiting")
        return
    await redis_client.lpush(key, *[f"{obj.inserted_id},{obj.url}" for obj in urls])
    logger.info(
        "Succesfully saved %s insertion info objects for parsed sales", len(urls)
    )


async def main():
    await ping_gateways()
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-l", "--limit", type=int)
    arg_parser.add_argument("-p", "--platform", type=ProductPlatform)
    args = arg_parser.parse_args()
    parser: SalesParser = get_container().instantiate(SalesParser)
    redis_client = Resolve(RedisClient)
    try:
        match args.platform:
            case None:
                save_info = await parser.parse_and_save_all(args.limit)
                await asyncio.gather(
                    save_parsed_urls(
                        redis_client, XBOX_REDIS_KEY, save_info[ProductPlatform.XBOX]
                    ),
                    save_parsed_urls(
                        redis_client, PSN_REDIS_KEY, save_info[ProductPlatform.PSN]
                    ),
                )
                await asyncio.gather(
                    parser.update_psn_details(
                        save_info[ProductPlatform.XBOX], timeout=1
                    ),
                    parser.update_xbox_details(save_info[ProductPlatform.PSN]),
                )
            case ProductPlatform.XBOX:
                items_for_update = await parser.parse_and_save_xbox(args.limit)
                await save_parsed_urls(redis_client, XBOX_REDIS_KEY, items_for_update)
                await parser.update_xbox_details(items_for_update)
            case ProductPlatform.PSN:
                items_for_update = await parser.parse_and_save_psn(args.limit)
                await save_parsed_urls(redis_client, PSN_REDIS_KEY, items_for_update)
                await parser.update_psn_details(items_for_update)
            case _:
                raise ValueError("Unsupported platform: %s" % args.platform)
    finally:
        await close_connections()


if __name__ == "__main__":
    asyncio.run(main())
