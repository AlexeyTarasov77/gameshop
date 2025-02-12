from datetime import timedelta
from typing import Protocol
from redis.asyncio import Redis
from secrets import token_urlsafe
from starlette.types import ASGIApp
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


class SessionMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        session_creator: SessionCreatorI,
        max_age: int,
        session_key_name: str = "session_id",
    ):
        self.app = app
        self.session_creator = session_creator
        self.session_key_name = session_key_name
        self.security_flags = "httponly; samesite=lax"
        self.max_age = max_age

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):  # pragma: no cover
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        send_func = send
        session_id: str | None = connection.cookies.get(self.session_key_name)
        if session_id is None:
            session_id = await self.session_creator.create({"cart": {}, "wishlist": []})

            async def send_wrapper(message: Message) -> None:
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    header_value = f"{self.session_key_name}={session_id}; Max-Age={self.max_age}; {self.security_flags}"
                    headers.append("Set-Cookie", header_value)
                await send(message)

            send_func = send_wrapper
        scope[self.session_key_name] = session_id

        await self.app(scope, receive, send_func)
