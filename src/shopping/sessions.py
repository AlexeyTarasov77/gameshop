from datetime import timedelta
from typing import Protocol
from fastapi import Request, Response
from secrets import token_urlsafe
from starlette.middleware.base import DispatchFunction, RequestResponseEndpoint
from redis.commands.json._util import JsonType
from gateways.db.exceptions import NotFoundError
from gateways.db import RedisClient


class SessionCreatorI(Protocol):
    async def create(self, initial_data: dict = {}) -> str: ...


class RedisSessionCreator:
    def __init__(self, ttl: timedelta, storage: RedisClient):
        self.ttl = ttl
        self.storage = storage
        self.prefix = "sessions"

    async def create(
        self,
        initial_data: dict = {},
    ) -> str:
        session_key = token_urlsafe(16)
        key = self.prefix + ":" + session_key
        await self.storage.json().set(key, "$", initial_data)
        await self.storage.expire(key, self.ttl)
        return session_key


class RedisSessionManager:
    def __init__(self, db: RedisClient, session_key: str):
        self._db = db
        self._prefix = "sessions"
        self.session_key = session_key

    @property
    def storage_key(self) -> str:
        return self._prefix + ":" + self.session_key

    async def set_to_session(self, path: str, data: JsonType, **kwargs) -> bool:
        return (
            await self._db.json().set(self.storage_key, path, data, **kwargs)
            is not None
        )

    async def delete_from_session(self, path: str) -> int:
        deleted_count = await self._db.json().delete(self.storage_key, path)
        if deleted_count == 0:
            raise NotFoundError()
        return deleted_count

    async def retrieve_from_session(self, *paths) -> list | None:
        return await self._db.json().get(self.storage_key, *paths)
