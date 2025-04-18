import asyncio
import sys
from pathlib import Path

sys.path.append((Path().parent / "src").absolute().as_posix())

from core.ioc import get_container
from main import lifespan
from gateways.gamesparser import SalesParser


async def main():
    try:
        limit = int(sys.argv[1])
    except Exception:
        limit = None
    parser: SalesParser = get_container().instantiate(SalesParser)
    async with lifespan():
        res = await parser.parse_and_save_all(limit)
        # async def update_psn_wrapper():
        #     # await asyncio.sleep(5 * 60)
        #     await parser.update_psn_details(res.psn, 1)
        await asyncio.gather(
            parser.update_psn_details(res.psn, 1), parser.update_xbox_details(res.xbox)
        )


if __name__ == "__main__":
    asyncio.run(main())
