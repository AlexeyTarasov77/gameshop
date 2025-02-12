from datetime import timedelta
from redis.asyncio import Redis
from secrets import token_urlsafe
from starlette.types import ASGIApp
from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import Message, Receive, Scope, Send


class SessionManager:
    def __init__(self, redis_client: Redis, session_id: str = ""):
        self._redis_client = redis_client
        self._session_ttl = timedelta(days=5)
        self._base_key = "sessions:%s"
        self.session_id = session_id

    async def new_session(self, initial_data: dict = {}) -> str:
        session_id = token_urlsafe(16)
        key = self._base_key % session_id
        await self._redis_client.json().set(key, "$", initial_data)
        await self._redis_client.expire(key, self._session_ttl)
        return session_id

    def _build_storing_key(self, session_id: str | None = None) -> str:
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError(
                "session_id should be passed to constructor or supplied to method"
            )
        return self._base_key % session_id

    async def set_to_session(
        self, path: str, data, session_id: str | None = None, **kwargs
    ) -> bool:
        return (
            await self._redis_client.json().set(
                self._build_storing_key(session_id), path, data, **kwargs
            )
            is not None
        )

    async def delete_from_session(
        self, path: str, session_id: str | None = None
    ) -> int:
        return await self._redis_client.json().delete(
            self._build_storing_key(session_id), path
        )

    async def get_from_session(self, *paths, session_id: str | None = None):
        return await self._redis_client.json().get(
            self._build_storing_key(session_id), *paths
        )


class SessionMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        session_manager: SessionManager,
        max_age: int,
        session_key_name: str = "session_id",
    ):
        self.app = app
        self.session_manager = session_manager
        self.session_key_name = session_key_name
        self.security_flags = "httponly; samesite=lax"
        self.max_age = max_age

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):  # pragma: no cover
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        session_id_was_empty = False

        if self.session_key_name not in connection.cookies:
            session_id_was_empty = True
            session_id = await self.session_manager.new_session({"cart": {}})
        else:
            session_id = connection.cookies[self.session_key_name]
        scope[self.session_key_name] = session_id

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start" and session_id_was_empty:
                headers = MutableHeaders(scope=message)
                header_value = f"{self.session_key_name}={session_id}; Max-Age={self.max_age}; {self.security_flags}"
                headers.append("Set-Cookie", header_value)
            await send(message)

        await self.app(scope, receive, send_wrapper)
