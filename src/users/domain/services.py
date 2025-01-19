import asyncio
import typing as t
from datetime import datetime, timedelta

from jwt.exceptions import InvalidTokenError

from core.service import BaseService
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import DatabaseError

from users.domain.interfaces import (
    HasherI,
    MailProviderI,
    TokenProviderI,
    UsersRepositoryI,
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
        activation_token_ttl: timedelta,
        auth_token_ttl: timedelta,
        activation_link: str,
    ) -> None:
        super().__init__(uow)
        from core.ioc import get_container

        container = get_container()
        self.hasher = t.cast(HasherI, container.resolve(HasherI))
        self.token_provider = t.cast(TokenProviderI, container.resolve(TokenProviderI))
        self.mail_provider = t.cast(MailProviderI, container.resolve(MailProviderI))
        self.activation_link = activation_link
        self.activation_token_ttl = activation_token_ttl
        self.auth_token_ttl = auth_token_ttl

    def _new_activation_token(self, uid: int):
        return self.token_provider.new_token({"uid": uid}, self.activation_token_ttl)

    async def signup(self, dto: CreateUserDTO) -> ShowUser:
        password_hash = self.hasher.hash(dto.password)
        try:
            async with self.uow as uow:
                repo = t.cast(UsersRepositoryI, uow.users_repo)
                user = await repo.create(
                    email=dto.email,
                    password_hash=password_hash,
                    photo_url=str(dto.photo_url),
                )
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(email=dto.email) from e
        activation_token = self._new_activation_token(user.id)
        email_body = f"""
            Здравствуйте, ваш аккаунт был успешно создан.
            Для активации аккаунта перейдите по ссылке ниже:
                {self.activation_link}
            И введите данный токен в поле ввода:
                {activation_token}
        """
        asyncio.create_task(
            self.mail_provider.send_mail_with_timeout(
                "Аккаунт успешно создан", email_body, user.email, timeout=3
            )
        )
        return ShowUser.model_validate(user)

    async def signin(self, dto: UserSignInDTO) -> str:
        try:
            async with self.uow as uow:
                repo = t.cast(UsersRepositoryI, uow.users_repo)
                user = await repo.get_by_email(dto.email)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(email=dto.email) from e
        if not user.is_active:
            raise UserIsNotActivatedError()
        if not self.hasher.compare(dto.password, user.password_hash):
            raise PasswordDoesNotMatchError()
        return self.token_provider.new_token({"uid": user.id}, self.auth_token_ttl)

    async def extract_user_id_from_token(self, token: str) -> int:
        try:
            token_payload = self.token_provider.extract_payload(token)
            user_id = token_payload["uid"]
            if int(user_id) < 1:
                raise ValueError()
            token_exp = datetime.fromtimestamp(token_payload["exp"])
        except (InvalidTokenError, ValueError, KeyError) as e:
            raise InvalidTokenServiceError("Token is invalid") from e
        if token_exp < datetime.now():
            raise InvalidTokenServiceError("Token is expired")
        return user_id

    async def activate_user(self, token: str) -> ShowUser:
        user_id = await self.extract_user_id_from_token(token)
        try:
            async with self.uow as uow:
                repo = t.cast(UsersRepositoryI, uow.users_repo)
                user = await repo.update_by_id(user_id, is_active=True)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(user_id=user_id) from e
        return ShowUser.model_validate(user)

    async def resend_activation_token(self, email: str) -> None:
        try:
            async with self.uow as uow:
                repo = t.cast(UsersRepositoryI, uow.users_repo)
                user = await repo.get_by_email(email)
            if user.is_active:
                raise UserAlreadyActivatedError
            token = self._new_activation_token(user.id)
            email_body = (
                f"Новый токен для активации аккаунта: {token}\n"
                "Перейдите по ссылке ниже для активации аккаунта\n"
                f"\t{self.activation_link % token}\t"
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
