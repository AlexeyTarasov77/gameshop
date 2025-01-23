import asyncio
from datetime import datetime, timedelta

from jwt.exceptions import InvalidTokenError

from core.service import BaseService
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import DatabaseError

from users.domain.interfaces import (
    MailProviderI,
    PasswordHasherI,
    StatefullTokenProviderI,
    TokenHasherI,
    StatelessTokenProviderI,
)
from users.schemas import CreateUserDTO, ShowUser, UserSignInDTO


class InvalidTokenServiceError(Exception): ...


class PasswordDoesNotMatchError(Exception): ...


class UserIsNotActivatedError(Exception): ...


class UserAlreadyActivatedError(Exception): ...


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
        self.password_hasher = password_hasher
        self.token_hasher = token_hasher
        self.jwt_token_provider = jwt_token_provider
        self.statefull_token_provider = statefull_token_provider
        self.mail_provider = mail_provider
        self.activation_link = activation_link
        self.activation_token_ttl = activation_token_ttl
        self.auth_token_ttl = auth_token_ttl

    async def signup(self, dto: CreateUserDTO) -> ShowUser:
        password_hash = self.password_hasher.hash(dto.password)
        try:
            async with self.uow as uow:
                user = await uow.users_repo.create_with_hashed_password(
                    dto,
                    password_hash=password_hash,
                )
                plain_token, token_obj = self.statefull_token_provider.new_token(
                    user.id, self.activation_token_ttl
                )
                await uow.tokens_repo.save(token_obj)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(
                email=dto.email, username=dto.username
            ) from e
        email_body = (
            f"Здравствуйте, {user.username}. Ваш аккаунт был успешно создан."
            "Для активации аккаунта перейдите по ссылке ниже и подтверждите активацию аккаунта:"
            f"\t{self.activation_link % plain_token}\t"
        )
        asyncio.create_task(
            self.mail_provider.send_mail_with_timeout(
                "Аккаунт успешно создан", email_body, user.email, timeout=3
            )
        )
        return ShowUser.model_validate(user)

    async def signin(self, dto: UserSignInDTO) -> str:
        try:
            async with self.uow as uow:
                user = await uow.users_repo.get_by_email(dto.email)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(email=dto.email) from e
        if not user.is_active:
            raise UserIsNotActivatedError()
        if not self.password_hasher.compare(dto.password, user.password_hash):
            raise PasswordDoesNotMatchError()
        return self.jwt_token_provider.new_token({"uid": user.id}, self.auth_token_ttl)

    async def extract_user_id_from_token(self, token: str) -> int:
        try:
            token_payload = self.jwt_token_provider.extract_payload(token)
            user_id = token_payload["uid"]
            if int(user_id) < 1:
                raise ValueError()
            token_exp = datetime.fromtimestamp(token_payload["exp"])
        except (InvalidTokenError, ValueError, KeyError) as e:
            raise InvalidTokenServiceError("Token is invalid") from e
        if token_exp < datetime.now():
            raise InvalidTokenServiceError("Token is expired")
        return user_id

    async def activate_user(self, plain_token: str) -> ShowUser:
        token_hash = self.statefull_token_provider.hasher.hash(plain_token)
        try:
            async with self.uow as uow:
                token = await uow.tokens_repo.get_by_hash(token_hash)
                user = await uow.users_repo.update_by_id(token.user_id, is_active=True)
                await uow.tokens_repo.delete_all_for_user(user.id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)() from e
        return ShowUser.model_validate(user)

    async def resend_activation_token(self, email: str) -> None:
        try:
            async with self.uow as uow:
                user = await uow.users_repo.get_by_email(email)
                await uow.tokens_repo.delete_all_for_user(user.id)
                plain_token, token_obj = self.statefull_token_provider.new_token(
                    user.id, self.activation_token_ttl
                )
                await uow.tokens_repo.save(token_obj)
            if user.is_active:
                raise UserAlreadyActivatedError
            email_body = (
                f"Новый токен для активации аккаунта: {plain_token}\n"
                "Перейдите по ссылке ниже для активации аккаунта\n"
                f"\t{self.activation_link % plain_token}\t"
            )
            asyncio.create_task(
                self.mail_provider.send_mail_with_timeout(
                    "Новый активационный токен",
                    email_body,
                    to=user.email,
                    timeout=3,
                )
            )
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(email=email) from e

    async def get_user(self, user_id: int) -> ShowUser:
        try:
            async with self.uow as uow:
                user = await uow.users_repo.get_by_id(user_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(user_id=user_id) from e
        return ShowUser.model_validate(user)
