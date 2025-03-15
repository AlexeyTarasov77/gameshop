import asyncio
import sys
from pathlib import Path


sys.path.append((Path().parent / "src").absolute().as_posix())

from gateways.steam import GamesForFarmAPIClient
from core.ioc import get_container
from main import lifespan


async def main():
    api_client: GamesForFarmAPIClient = get_container().instantiate(
        GamesForFarmAPIClient
    )
    async with lifespan():
        await api_client.fetch_and_save()


if __name__ == "__main__":
    asyncio.run(main())
