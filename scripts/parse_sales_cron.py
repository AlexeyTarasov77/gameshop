import asyncio
import sys
from pathlib import Path

sys.path.append((Path().parent / "src").absolute().as_posix())

from core.ioc import get_container
from main import lifespan
from gateways.gamesparser import SalesParser


async def main():
    parser: SalesParser = get_container().instantiate(SalesParser)
    try:
        limit = int(sys.argv[1])
    except IndexError:
        limit = None
    async with lifespan():
        await parser.parse_and_save(limit)


if __name__ == "__main__":
    asyncio.run(main())
