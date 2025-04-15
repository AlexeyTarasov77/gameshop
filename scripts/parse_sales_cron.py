import asyncio
import sys
from pathlib import Path

sys.path.append((Path().parent / "src").absolute().as_posix())

from core.ioc import get_container
from main import lifespan
from gateways.gamesparser import SalesParser


async def main():
    parser: SalesParser = get_container().instantiate(SalesParser)
    async with lifespan():
        await parser.parse_and_save()


if __name__ == "__main__":
    asyncio.run(main())
