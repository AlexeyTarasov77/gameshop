import asyncio
from datetime import datetime, timedelta

from jwt.exceptions import InvalidTokenError as InvalidJwtTokenError

from core.services.base import BaseService
from core.services.exceptions import ServiceError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import AlreadyExistsError, DatabaseError, NotFoundError

from users.domain.interfaces import (
    MailProviderI,
    PasswordHasherI,
    StatefullTokenProviderI,
    TokenHasherI,
    StatelessTokenProviderI,
)
from users.schemas import CreateUserDTO, ShowUser, ShowUserWithRole, UserSignInDTO


class TokenError(ServiceError): ...


class ExpiredTokenError(TokenError):
    def __init__(self):
        super().__init__("Token expired! Please refresh your token.")


class InvalidTokenError(TokenError):
    def __init__(self):
        super().__init__("Invalid token. Please obtain a new token and try again.")


class UserIsNotActivatedError(ServiceError):
    def __init__(self):
        super().__init__(
            "User isn't activated. Check your email to activate account and try to signin again!"
        )


class InvalidCredentialsError(ServiceError):
    def __init__(self):
        super().__init__("Invalid email or password")


class UserAlreadyActivatedError(ServiceError):
    def __init__(self):
        super().__init__("User already activated!")


class UsersService(BaseService):
    entity_name = "User"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        token_hasher: TokenHasherI,
        password_hasher: PasswordHasherI,
        jwt_token_provider: StatelessTokenProviderI,
        statefull_token_provider: StatefullTokenProviderI,
        mail_provider: MailProviderI,
        activation_token_ttl: timedelta,
        auth_token_ttl: timedelta,
        activation_link: str,
    ) -> None:
        super().__init__(uow)
        self._password_hasher = password_hasher
        self._token_hasher = token_hasher
        self._jwt_token_provider = jwt_token_provider
        self._statefull_token_provider = statefull_token_provider
        self._mail_provider = mail_provider
        self._activation_link = activation_link
        self._activation_token_ttl = activation_token_ttl
        self._auth_token_ttl = auth_token_ttl

    async def signup(self, dto: CreateUserDTO) -> ShowUser:
        password_hash = self._password_hasher.hash(dto.password)
        try:
            async with self._uow as uow:
                user = await uow.users_repo.create_with_hashed_password(
                    dto,
                    password_hash=password_hash,
                )
                plain_token, token_obj = self._statefull_token_provider.new_token(
                    user.id, self._activation_token_ttl
                )
                await uow.tokens_repo.save(token_obj)
        except AlreadyExistsError as e:
            exc = e
            async with self._uow as uow:
                existed_user = await uow.users_repo.get_by_email(dto.email)
                if not existed_user.is_active:
                    exc = UserIsNotActivatedError()
            raise exc

        except DatabaseError as e:
            raise self._exception_mapper.map(e)(
                email=dto.email, username=dto.username
            ) from e
        email_body = (
            f"Здравствуйте, {user.username}. Ваш аккаунт был успешно создан."
            "Для активации аккаунта перейдите по ссылке ниже и подтверждите активацию аккаунта:"
            f"\t{self._activation_link % plain_token}\t"
        )
        asyncio.create_task(
            self._mail_provider.send_mail_with_timeout(
                "Аккаунт успешно создан", email_body, user.email, timeout=3
            )
        )
        return ShowUser.model_validate(user)

    async def signin(self, dto: UserSignInDTO) -> str:
        try:
            async with self._uow as uow:
                user = await uow.users_repo.get_by_email(dto.email)
        except NotFoundError as e:
            raise InvalidCredentialsError() from e
        except DatabaseError as e:
            raise self._exception_mapper.map(e)(email=dto.email) from e
        if not user.is_active:
            raise UserIsNotActivatedError()
        if not self._password_hasher.compare(dto.password, user.password_hash):
            raise InvalidCredentialsError()
        return self._jwt_token_provider.new_token(
            {"uid": user.id}, self._auth_token_ttl
        )

    async def extract_user_id_from_token(self, token: str) -> int:
        try:
            token_payload = self._jwt_token_provider.extract_payload(token)
            user_id = token_payload["uid"]
            if int(user_id) < 1:
                raise ValueError()
            token_exp = datetime.fromtimestamp(token_payload["exp"])
        except (InvalidJwtTokenError, ValueError, KeyError) as e:
            raise InvalidTokenError() from e
        if token_exp < datetime.now():
            raise ExpiredTokenError()
        return user_id

    async def activate_user(self, plain_token: str) -> ShowUser:
        token_hash = self._statefull_token_provider.hasher.hash(plain_token)
        try:
            async with self._uow as uow:
                token = await uow.tokens_repo.get_by_hash(token_hash)
                user = await uow.users_repo.mark_as_active(token.user_id)
                await uow.tokens_repo.delete_all_for_user(user.id)
        except DatabaseError as e:
            raise self._exception_mapper.map(e)() from e
        return ShowUser.model_validate(user)

    async def resend_activation_token(self, email: str) -> None:
        try:
            async with self._uow as uow:
                user = await uow.users_repo.get_by_email(email)
                await uow.tokens_repo.delete_all_for_user(user.id)
                plain_token, token_obj = self._statefull_token_provider.new_token(
                    user.id, self._activation_token_ttl
                )
                await uow.tokens_repo.save(token_obj)
            if user.is_active:
                raise UserAlreadyActivatedError()
            email_body = (
                f"Новый токен для активации аккаунта: {plain_token}\n"
                "Перейдите по ссылке ниже для активации аккаунта\n"
                f"\t{self._activation_link % plain_token}\t"
            )
            asyncio.create_task(
                self._mail_provider.send_mail_with_timeout(
                    "Новый активационный токен",
                    email_body,
                    to=user.email,
                    timeout=3,
                )
            )
        except DatabaseError as e:
            raise self._exception_mapper.map(e)(email=email) from e

    async def get_user(self, user_id: int) -> ShowUserWithRole:
        try:
            async with self._uow as uow:
                user, is_admin = await uow.users_repo.get_by_id_and_check_is_admin(
                    user_id
                )
        except DatabaseError as e:
            raise self._exception_mapper.map(e)(user_id=user_id) from e
        user.is_admin = is_admin
        return ShowUserWithRole.model_validate(user)

    async def check_is_user_admin(self, user_id: int) -> bool:
        try:
            async with self._uow as uow:
                return await uow.admins_repo.check_exists(user_id)
        except DatabaseError as e:
            raise self._exception_mapper.map(e)(user_id=user_id) from e
