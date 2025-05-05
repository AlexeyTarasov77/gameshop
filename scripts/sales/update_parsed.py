from argparse import ArgumentParser
import sys
import os
import asyncio
from pathlib import Path


sys.path.append((Path().parent.parent / "src").absolute().as_posix())

from config import ConfigMode

if not os.environ.get("MODE"):
    os.environ["MODE"] = ConfigMode.LOCAL

from parse_and_save import PSN_REDIS_KEY, XBOX_REDIS_KEY
from gateways.db import RedisClient
from products.domain.interfaces import SavedGameInfo
from products.models import ProductPlatform
from core.ioc import get_container, Resolve
from main import ping_gateways, close_connections
from gateways.gamesparser import SalesParser


async def retrieve_saved_info(key: str, redis_client: RedisClient):
    saved_info_raw: list[str] = await redis_client.lrange(key, 0, -1)
    saved_info: list[SavedGameInfo] = []
    for s in saved_info_raw:
        id, _, url = s.partition(",")
        saved_info.append(SavedGameInfo(int(id), url))
    return saved_info


async def main():
    await ping_gateways()
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-p", "--platform", type=ProductPlatform)
    args = arg_parser.parse_args()
    parser: SalesParser = get_container().instantiate(SalesParser)
    redis_client = Resolve(RedisClient)
    try:
        match args.platform:
            case None:
                xbox_saved_info = await retrieve_saved_info(
                    XBOX_REDIS_KEY, redis_client
                )
                psn_saved_info = await retrieve_saved_info(PSN_REDIS_KEY, redis_client)
                await asyncio.gather(
                    parser.update_psn_details(
                        psn_saved_info,
                        timeout=1,
                    ),
                    parser.update_xbox_details(xbox_saved_info),
                )
            case ProductPlatform.XBOX:
                items_for_update = await retrieve_saved_info(
                    XBOX_REDIS_KEY, redis_client
                )
                await parser.update_xbox_details(items_for_update)
            case ProductPlatform.PSN:
                items_for_update = await retrieve_saved_info(
                    PSN_REDIS_KEY, redis_client
                )
                await parser.update_psn_details(items_for_update)
            case _:
                raise ValueError("Unsupported platform: %s" % args.platform)
    finally:
        await close_connections()


if __name__ == "__main__":
    asyncio.run(main())
