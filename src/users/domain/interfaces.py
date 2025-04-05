import typing as t
from datetime import timedelta

from core.utils import UnspecifiedType
from mailing.domain.interfaces import MailingTemplate
from users.models import Token, TokenScopes, User
from users.schemas import CreateUserDTO


class EmailTemplatesI(t.Protocol):
    async def signup(self, username: str, link: str) -> str | MailingTemplate: ...
    async def password_reset(
        self, username: str, link: str
    ) -> str | MailingTemplate: ...
    async def new_activation_token(
        self, username: str, token: str, link: str
    ) -> str | MailingTemplate: ...
    async def email_verification(
        self, username: str, link: str
    ) -> str | MailingTemplate: ...


class UsersRepositoryI(t.Protocol):
    async def create_with_hashed_password(
        self, dto: CreateUserDTO, password_hash: bytes, photo_url: str | None
    ) -> User: ...

    async def mark_as_active(self, user_id: int) -> User: ...
    async def set_new_password(self, user_id: int, password_hash: bytes) -> None: ...
    async def check_exists_active(self, user_id: int) -> bool: ...

    async def get_by_email(self, email: str) -> User: ...
    async def update_by_id(
        self,
        user_id: int,
        username: str | None = None,
        photo_url: str | None | UnspecifiedType = ...,
        email: str | None = None,
    ) -> User: ...
    async def get_by_id(self, user_id: int, is_active: bool | None = None) -> User: ...
    async def get_by_id_and_check_is_admin(self, user_id: int) -> tuple[User, bool]: ...


class AdminsRepositoryI(t.Protocol):
    async def check_exists(self, user_id: int) -> bool: ...


class TokensRepositoryI(t.Protocol):
    async def save(self, token: Token) -> None: ...

    async def get_by_hash(self, hash: bytes, scope: TokenScopes) -> Token: ...

    async def delete_all_for_user(self, user_id: int, scope: TokenScopes) -> None: ...


class BaseHasherI(t.Protocol):
    def hash(self, s: str) -> bytes: ...

    def compare(self, s: str, hash: bytes) -> bool: ...


class PasswordHasherI(BaseHasherI): ...


class TokenHasherI(BaseHasherI): ...


class StatelessTokenProviderI(t.Protocol):
    def new_token(self, payload: dict[str, t.Any], expires_in: timedelta) -> str: ...

    def extract_payload(self, token: str) -> dict[str, t.Any]: ...


class StatefullTokenProviderI(t.Protocol):
    def new_token(
        self, user_id: int, expires_in: timedelta, scope: TokenScopes
    ) -> tuple[str, Token]: ...
