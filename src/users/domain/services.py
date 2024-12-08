import asyncio
import typing as t
from datetime import timedelta

from core.http.utils import save_upload_file
from core.service import BaseService
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import DatabaseError
from users.domain.interfaces import (
    HasherI,
    MailProviderI,
    TokenProviderI,
    UsersRepositoryI,
)
from users.schemas import CreateUserDTO


class UsersService(BaseService):
    entity_name = "User"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        hasher: HasherI,
        token_provider: TokenProviderI,
        activation_token_ttl: timedelta,
        activation_link: str,
        mail_provider: MailProviderI,
    ) -> None:
        super().__init__(uow)
        self.hasher = hasher
        self.token_provider = token_provider
        self.mail_provider = mail_provider
        self.activation_link = activation_link
        self.activation_token_ttl = activation_token_ttl

    async def signup(self, dto: CreateUserDTO) -> str:
        password_hash = self.hasher.hash(dto.password)
        try:
            async with self.uow as uow:
                if dto.photo:
                    uploaded_to = save_upload_file(dto.photo)
                repo = t.cast(UsersRepositoryI, uow.users_repo)
                user = await repo.create(dto.email, password_hash, uploaded_to)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(**dto.model_dump(include=["email"])) from e
        activation_token = self.token_provider.new_token({"uid": user.id}, self.activation_token_ttl)
        email_body = f"""
            Здравствуйте, ваш аккаунт был успешно создан.
            Для активации аккаунта перейдите по ссылке ниже:
                {self.activation_link}
            И введите данный токен в поле ввода:
                {activation_token}
        """
        asyncio.to_thread(self.mail_provider.send_mail, "Аккаунт успешно создан", email_body, user.email)
        return activation_token
