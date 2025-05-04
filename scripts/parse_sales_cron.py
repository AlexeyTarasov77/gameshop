import os

import asyncio
import sys
from pathlib import Path
from argparse import ArgumentParser


sys.path.append((Path().parent / "src").absolute().as_posix())

from config import ConfigMode

if not os.environ.get("MODE"):
    os.environ["MODE"] = ConfigMode.LOCAL

from products.models import ProductPlatform
from core.ioc import get_container
from main import lifespan
from gateways.gamesparser import SalesParser


async def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-l", "--limit", type=int)
    arg_parser.add_argument("-p", "--platform", type=ProductPlatform)
    args = arg_parser.parse_args()
    parser: SalesParser = get_container().instantiate(SalesParser)
    async with lifespan():
        match args.platform:
            case None:
                save_info = await parser.parse_and_save_all(args.limit)
                await asyncio.gather(
                    parser.update_psn_details(
                        save_info[ProductPlatform.XBOX], timeout=1
                    ),
                    parser.update_xbox_details(save_info[ProductPlatform.PSN]),
                )
            case ProductPlatform.XBOX:
                items_for_update = await parser.parse_and_save_xbox(args.limit)
                await parser.update_xbox_details(items_for_update)
            case ProductPlatform.PSN:
                items_for_update = await parser.parse_and_save_psn(args.limit)
                await parser.update_psn_details(items_for_update)
            case _:
                raise ValueError("Unsupported platform: %s" % args.platform)


if __name__ == "__main__":
    asyncio.run(main())
