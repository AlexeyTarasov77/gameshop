from collections.abc import Sequence
from core.logging import AbstractLogger
import sys
import os
import math
from pathlib import Path


sys.path.append((Path().parent.parent / "src").absolute().as_posix())

from config import ConfigMode

if not os.environ.get("MODE"):
    os.environ["MODE"] = ConfigMode.LOCAL

from core.ioc import Resolve
from core.utils import chunkify
from gateways.db.redis_gateway.main import RedisClient
from products.domain.services import ProductsService
from products.models import ProductPlatform
from gateways.gamesparser.client import SalesParser


XBOX_REDIS_KEY = "parsed_xbox"
PSN_REDIS_KEY = "parsed_psn"
UPDATE_CHUNK_SIZE = 200


def get_redis_key_by_platform(platform: ProductPlatform):
    return {
        ProductPlatform.XBOX: XBOX_REDIS_KEY,
        ProductPlatform.PSN: PSN_REDIS_KEY,
    }[platform]


async def save_unprocessed_ids(key: str, ids: Sequence[int]):
    """
    Saves ids of most recently parsed and saved sales
    which could be retrieved for further processing
    """
    redis_client = Resolve(RedisClient)
    logger = Resolve(AbstractLogger)
    await redis_client.delete(key)
    if not ids:
        logger.info("No unprocessed ids to save")
        return
    await redis_client.lpush(key, *ids)
    logger.info("Succesfully saved lastly inserted ids", count=len(ids), key=key)


async def update_sales_details(
    ids: Sequence[int], platform: ProductPlatform, parser: SalesParser
):
    service = Resolve(ProductsService)
    logger = Resolve(AbstractLogger)
    urls_mapping = await service.get_urls_mapping(ids)
    # overwrite ids with those from urls mapping to ensure they are in corresponding order
    ids = list(urls_mapping.keys())
    key = get_redis_key_by_platform(platform)
    total_chunks = math.ceil(len(urls_mapping) / UPDATE_CHUNK_SIZE)
    total_updated = 0
    for i, chunk in enumerate(
        chunkify(list(urls_mapping.items()), UPDATE_CHUNK_SIZE), 1
    ):
        urls_mapping_chunk = dict(chunk)
        await parser.update_for_platform(platform, urls_mapping_chunk)
        logger.info(
            "Chunk updated", chunk_num=i, total_chunks=total_chunks, platform=platform
        )
        await save_unprocessed_ids(key, ids[UPDATE_CHUNK_SIZE * i :])
        total_updated += len(urls_mapping_chunk)
    logger.info("Chunked update completed", total_updated=total_updated)
