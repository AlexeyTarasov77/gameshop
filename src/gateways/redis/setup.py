import asyncio
from logging import Logger
import sys
from pathlib import Path

sys.path.append(Path().absolute().as_posix())
sys.path.append((Path() / "src").absolute().as_posix())
from redis import ResponseError
from redis.asyncio import Redis
from gateways.redis.main import indexes
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.field import TextField, TagField
from sales import APP_LABEL as SALES_APP_LABEL
from core.ioc import Resolve


async def main(r: Redis):
    logger = Resolve(Logger)
    logger.info("Creating index for: %s", SALES_APP_LABEL)
    idx_sales_schema = (
        TextField("$.name", as_name="name"),
        TagField("$.category", as_name="category"),
        TagField("$.prices.*.region", as_name="price_regions"),
    )
    try:
        await r.ft(indexes[SALES_APP_LABEL].name).create_index(
            idx_sales_schema,
            definition=IndexDefinition(
                prefix=[indexes[SALES_APP_LABEL].for_prefix], index_type=IndexType.JSON
            ),
        )
    except ResponseError as e:
        if "already exists" in str(e):
            logger.warning("Index already exists! Skipping")
        else:
            raise e
    else:
        logger.info("Index succesfully created")
    await r.aclose()  # type: ignore


if __name__ == "__main__":
    r = Resolve(Redis)
    asyncio.run(main(r))
