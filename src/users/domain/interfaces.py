import typing as t
from datetime import timedelta

from users.models import Token, User
from users.schemas import CreateUserDTO


class UsersRepositoryI(t.Protocol):
    async def create_with_hashed_password(
        self, dto: CreateUserDTO, password_hash: bytes
    ) -> User: ...

    async def mark_as_active(self, user_id: int) -> User: ...

    async def get_by_email(self, email: str) -> User: ...

    async def get_by_id(self, user_id: int) -> User: ...


class AdminsRepositoryI(t.Protocol):
    async def check_exists(self, user_id: int) -> bool: ...


class TokensRepositoryI(t.Protocol):
    async def save(self, token: Token) -> None: ...

    async def get_by_hash(self, hash: bytes) -> Token: ...

    async def delete_all_for_user(self, user_id: int) -> None: ...


class BaseHasherI(t.Protocol):
    def hash(self, s: str) -> bytes: ...

    def compare(self, s: str, hash: bytes) -> bool: ...


class PasswordHasherI(BaseHasherI): ...


class TokenHasherI(BaseHasherI): ...


class StatelessTokenProviderI(t.Protocol):
    def new_token(self, payload: dict[str, t.Any], expires_in: timedelta) -> str: ...

    def extract_payload(self, token: str) -> dict[str, t.Any]: ...


class StatefullTokenProviderI(t.Protocol):
    hasher: TokenHasherI

    def new_token(self, user_id: int, expires_in: timedelta) -> tuple[str, Token]: ...


class MailProviderI(t.Protocol):
    async def send_mail_with_timeout(
        self,
        subject: str,
        body: str,
        to: str,
        from_: str | None = None,
        *,
        timeout: float = 3,
    ) -> None: ...
