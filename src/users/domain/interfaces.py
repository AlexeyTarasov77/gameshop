import typing as t
from datetime import timedelta

from users.models import User


class UsersRepositoryI(t.Protocol):
    async def create(self, **data) -> User: ...

    async def update_by_id(self, user_id: int, **data) -> User: ...

    async def get_by_email(self, email: str) -> User: ...


class HasherI(t.Protocol):
    def hash(self, password: str) -> bytes: ...

    def compare(self, password: str, hashed_password: bytes) -> bool: ...


class TokenProviderI(t.Protocol):
    def new_token(self, payload: dict[str, t.Any], expires_in: timedelta) -> str: ...

    def extract_payload(self, token: str) -> dict[str, t.Any]: ...


class MailProviderI(t.Protocol):
    async def send_mail(
        self, subject: str, body: str, to: str, from_: str | None = None
    ) -> None: ...
