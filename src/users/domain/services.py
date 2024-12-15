import asyncio
import typing as t
from datetime import datetime, timedelta

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

    async def signup(self, dto: CreateUserDTO) -> ShowUser:
        password_hash = self.hasher.hash(dto.password)
        try:
            async with self.uow as uow:
                repo = t.cast(UsersRepositoryI, uow.users_repo)
                user = await repo.create(dto.email, password_hash, str(dto.photo_url))
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(email=dto.email) from e
        activation_token = self.token_provider.new_token({"uid": user.id}, self.activation_token_ttl)
        email_body = f"""
            Здравствуйте, ваш аккаунт был успешно создан.
            Для активации аккаунта перейдите по ссылке ниже:
                {self.activation_link}
            И введите данный токен в поле ввода:
                {activation_token}
        """
        asyncio.create_task(
            self.mail_provider.send_mail("Аккаунт успешно создан", email_body, user.email)
        )
        return user.to_read_model()

    async def signin(self, dto: UserSignInDTO) -> str:
        try:
            async with self.uow as uow:
                repo = t.cast(UsersRepositoryI, uow.users_repo)
                user = await repo.get_by_email(dto.email)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(email=dto.email) from e
        if not self.hasher.compare(dto.password, user.password_hash):
            raise PasswordDoesNotMatchError("Passwords doesn't match")
        return self.token_provider.new_token({"uid": user.id}, self.auth_token_ttl)

    async def activate_user(self, token: str) -> ShowUser:
        try:
            token_payload = self.token_provider.extract_payload(token)
            user_id = token_payload["uid"]
            if int(user_id) < 1:
                raise ValueError()
            token_exp = datetime.fromtimestamp(token_payload["exp"])
        except Exception as e:
            raise InvalidTokenServiceError("Token is invalid") from e
        if token_exp < datetime.now():
            raise InvalidTokenServiceError("Token is expired")
        try:
            async with self.uow as uow:
                repo = t.cast(UsersRepositoryI, uow.users_repo)
                user = await repo.update(user_id, is_active=True)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(user_id=user_id) from e
        return user.to_read_model()
