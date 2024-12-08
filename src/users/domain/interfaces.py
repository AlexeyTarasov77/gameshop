import typing as t
from datetime import timedelta

from users.models import User


class UsersRepositoryI(t.Protocol):
    async def create(self, email: str, password_hash: bytes, photo_url: str) -> User: ...


class HasherI(t.Protocol):
    def hash(self, password: str) -> bytes: ...

    def compare(self, password: str, hashed_password: bytes) -> bool: ...


class TokenProviderI(t.Protocol):
    def new_token(self, payload: dict[str, t.Any], expires_in: timedelta): ...


class MailProviderI(t.Protocol):
    def send_mail(self, subject: str, body: str, to: str, from_: str | None = None, ): ...
