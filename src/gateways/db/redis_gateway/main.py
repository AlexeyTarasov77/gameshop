import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from json import JSONDecoder, JSONEncoder
from logging import Logger

from redis.commands.search.field import Field
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.asyncio import Redis, ResponseError
from redis.commands.json import JSON


class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        try:
            return str(o)
        except Exception:
            return super().default(o)


@dataclass
class IndexMetadata:
    for_prefix: str
    name: str


@dataclass
class IndexSchema:
    metadata: IndexMetadata
    _schema: Sequence[Field]
    _type: IndexType = IndexType.JSON


class AvailableIndexes(Enum): ...


class RedisClient(Redis):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.indexes: tuple[IndexSchema] = tuple()

    @classmethod
    def from_url(
        cls,
        url: str,
        **kwargs,
    ) -> Redis:
        return super().from_url(url, decode_responses=True, **kwargs)

    def json(self, encoder=CustomJSONEncoder(), decoder=JSONDecoder()) -> JSON:
        return super().json(encoder, decoder)

    async def _create_index(self, idx: IndexSchema):
        from core.ioc import Resolve

        logger = Resolve(Logger)
        logger.info("Creating index: %s", idx.metadata.name)
        try:
            await self.ft(idx.metadata.name).create_index(
                idx._schema,
                definition=IndexDefinition(
                    prefix=[idx.metadata.for_prefix],
                    index_type=idx._type,
                ),
            )
        except ResponseError as e:
            if "already exists" in str(e):
                logger.warning("Index already exists! Skipping")
            else:
                raise e
        else:
            logger.info("Index succesfully created")

    async def setup(self):
        await asyncio.gather(*[self._create_index(idx) for idx in self.indexes])
