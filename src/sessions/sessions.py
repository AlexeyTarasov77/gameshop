from datetime import timedelta
from typing import Protocol
from fastapi import Request, Response
from redis.asyncio import Redis
from secrets import token_urlsafe
from starlette.types import ASGIApp
from starlette.middleware.base import DispatchFunction, RequestResponseEndpoint
from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import Message, Receive, Scope, Send

from gateways.db.exceptions import NotFoundError


class SessionCreatorI(Protocol):
    async def create(self, initial_data: dict = {}) -> str: ...


class RedisSessionCreator:
    def __init__(self, ttl: timedelta, storage: Redis):
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
    def __init__(self, storage: Redis, session_key: str):
        self._storage = storage
        self._prefix = "sessions"
        self.session_key = session_key

    @classmethod
    def get_for_session(cls, session_key: str):
        from core.ioc import Resolve

        return cls(Resolve(Redis), session_key)

    @property
    def storage_key(self) -> str:
        return self._prefix + ":" + self.session_key

    async def set_to_session(self, path: str, data, **kwargs) -> bool:
        return (
            await self._storage.json().set(self.storage_key, path, data, **kwargs)
            is not None
        )

    async def delete_from_session(self, path: str) -> int:
        deleted_count = await self._storage.json().delete(self.storage_key, path)
        if deleted_count == 0:
            raise NotFoundError()
        return deleted_count

    async def retrieve_from_session(self, *paths) -> list | None:
        return await self._storage.json().get(self.storage_key, *paths)


def session_middleware(
    session_creator: SessionCreatorI,
    max_age: int | timedelta,
    session_key_name: str = "session_id",
) -> DispatchFunction:
    async def create_session(
        req: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        nonlocal max_age
        session_key: str | None = req.cookies.get(session_key_name)
        if session_key is None:
            session_key = await session_creator.create({"cart": {}, "wishlist": []})
        req.scope[session_key_name] = session_key
        resp = await call_next(req)
        if isinstance(max_age, timedelta):
            max_age = int(max_age.total_seconds())
        resp.set_cookie(
            session_key_name,
            session_key,
            max_age,
            httponly=True,
            samesite="none",
            secure=True,
        )
        return resp

    return create_session
