import asyncio
from datetime import datetime, timedelta
from logging import Logger

from jwt.exceptions import InvalidTokenError as InvalidJwtTokenError

from core.services.base import BaseService
from core.services import exceptions as exc
from core.uow import AbstractUnitOfWork
from core.utils import save_upload_file
from gateways.db.exceptions import AlreadyExistsError, NotFoundError

from sessions.domain.interfaces import SessionCopierI
from users.domain.interfaces import (
    EmailTemplatesI,
    MailProviderI,
    PasswordHasherI,
    StatefullTokenProviderI,
    TokenHasherI,
    StatelessTokenProviderI,
    TokensRepositoryI,
)
from users.models import TokenScopes
from users.schemas import CreateUserDTO, ShowUser, ShowUserWithRole, UserSignInDTO


class UsersService(BaseService):
    entity_name = "User"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        logger: Logger,
        email_templates: EmailTemplatesI,
        token_hasher: TokenHasherI,
        password_hasher: PasswordHasherI,
        jwt_token_provider: StatelessTokenProviderI,
        statefull_token_provider: StatefullTokenProviderI,
        mail_provider: MailProviderI,
        session_copier: SessionCopierI,
        activation_token_ttl: timedelta,
        auth_token_ttl: timedelta,
        password_reset_token_ttl: timedelta,
        activation_link: str,
        password_reset_link: str,
    ) -> None:
        super().__init__(uow, logger)
        self._password_hasher = password_hasher
        self._token_hasher = token_hasher
        self._jwt_token_provider = jwt_token_provider
        self._session_copier = session_copier
        self._statefull_token_provider = statefull_token_provider
        self._mail_provider = mail_provider
        self._activation_link = activation_link
        self._password_reset_link = password_reset_link
        self._activation_token_ttl = activation_token_ttl
        self._password_reset_token_ttl = password_reset_token_ttl
        self._auth_token_ttl = auth_token_ttl
        self._email_templates = email_templates

    async def _create_and_save_token(
        self, user_id: int, scope: TokenScopes, repo: TokensRepositoryI
    ) -> str:
        match scope:
            case TokenScopes.ACTIVATION:
                ttl = self._activation_token_ttl
            case TokenScopes.PASSWORD_RESET:
                ttl = self._password_reset_token_ttl

        plain_token, token_obj = self._statefull_token_provider.new_token(
            user_id, ttl, scope
        )
        await repo.save(token_obj)
        return plain_token

    async def signup(self, dto: CreateUserDTO) -> ShowUser:
        photo_url = await save_upload_file(dto.photo) if dto.photo else None
        self._logger.info(
            "Signing up user with email: %s, username: %s", dto.email, dto.username
        )
        password_hash = self._password_hasher.hash(dto.password)
        try:
            async with self._uow as uow:
                user = await uow.users_repo.create_with_hashed_password(
                    dto, password_hash, photo_url
                )
                # deliberately creating token inside transaction to avoid user creating in case of error
                plain_token = await self._create_and_save_token(
                    user.id,
                    TokenScopes.ACTIVATION,
                    uow.tokens_repo,
                )
        except AlreadyExistsError as e:
            self._logger.info("User with email=%s already exists", dto.email)
            error = e
            async with self._uow as uow:
                existed_user = await uow.users_repo.get_by_email(dto.email)
                if not existed_user.is_active:
                    self._logger.info("Existent user is not activated")
                    error = exc.UserIsNotActivatedError()
            raise error
        asyncio.create_task(
            self._mail_provider.send_mail_with_timeout(
                "Аккаунт успешно создан",
                self._email_templates.welcome(
                    user.username, self._activation_link % plain_token
                ),
                user.email,
            )
        )
        self._logger.info(
            "User %s has succesfully signed up. Activation token sent to %s",
            user.id,
            user.email,
        )
        return ShowUser.model_validate(user)

    async def signin(self, dto: UserSignInDTO, session_key: str) -> str:
        self._logger.info("Signing in user with email: %s", dto.email)
        try:
            async with self._uow as uow:
                user = await uow.users_repo.get_by_email(dto.email)
        except NotFoundError as e:
            self._logger.warning(
                "User with provided email not found. Email: %s", dto.email
            )
            raise exc.InvalidCredentialsError() from e
        if not user.is_active:
            self._logger.warning(
                "Attempt to sign in from not activated user %s", user.id
            )
            raise exc.UserIsNotActivatedError()
        if not self._password_hasher.compare(dto.password, user.password_hash):
            self._logger.info("Passwords does not match for user %s", user.id)
            raise exc.InvalidCredentialsError()
        token = self._jwt_token_provider.new_token(
            {"uid": user.id}, self._auth_token_ttl
        )
        await self._session_copier.copy_for_user(session_key, user.id)
        self._logger.info("User %s succesfully signed in", user.id)
        return token

    async def send_password_reset_token(self, user_email: str):
        self._logger.info("Password reset request for user %s", user_email)
        try:
            async with self._uow as uow:
                user = await uow.users_repo.get_by_email(user_email)
                plain_token, token_obj = self._statefull_token_provider.new_token(
                    user.id, self._password_reset_token_ttl, TokenScopes.PASSWORD_RESET
                )
                await uow.tokens_repo.save(token_obj)
        except NotFoundError:
            self._logger.info("User not found. Email: %s", user_email)
            raise exc.EntityNotFoundError(self.entity_name, email=user_email)
        asyncio.create_task(
            self._mail_provider.send_mail_with_timeout(
                "Сброс пароля",
                self._email_templates.password_reset(
                    user.username, self._password_reset_link % plain_token
                ),
                user.email,
            )
        )
        self._logger.info("Password reset request succesfully processed")

    async def update_password(self, new_password: str, plain_token: str):
        self._logger.info("Updating resetted password by token")
        token_hash = await asyncio.to_thread(self._token_hasher.hash, plain_token)
        hashed_password = await asyncio.to_thread(
            self._password_hasher.hash, new_password
        )
        try:
            async with self._uow as uow:
                token = await uow.tokens_repo.get_by_hash(
                    token_hash, TokenScopes.PASSWORD_RESET
                )
                await uow.users_repo.set_new_password(token.user_id, hashed_password)
                await uow.tokens_repo.delete_all_for_user(
                    token.user_id, TokenScopes.PASSWORD_RESET
                )
        except NotFoundError:
            self._logger.info("Supplied token for password reset not found")
            raise exc.InvalidTokenError()
        self._logger.info("Password succesfully updated for user: %s", token.user_id)

    async def extract_user_id_from_token(self, token: str) -> int:
        try:
            token_payload = self._jwt_token_provider.extract_payload(token)
            user_id = token_payload["uid"]
            if int(user_id) < 1:
                raise ValueError()
            token_exp = datetime.fromtimestamp(token_payload["exp"])
        except (InvalidJwtTokenError, ValueError, KeyError) as e:
            raise exc.InvalidTokenError() from e
        if token_exp < datetime.now():
            raise exc.ExpiredTokenError()
        return user_id

    async def activate_user(self, plain_token: str) -> ShowUser:
        self._logger.info("Activating user")
        token_hash = await asyncio.to_thread(self._token_hasher.hash, plain_token)
        try:
            async with self._uow as uow:
                token = await uow.tokens_repo.get_by_hash(
                    token_hash, TokenScopes.ACTIVATION
                )
                user = await uow.users_repo.mark_as_active(token.user_id)
                await uow.tokens_repo.delete_all_for_user(
                    user.id, TokenScopes.ACTIVATION
                )
        except NotFoundError:
            self._logger.info("Supplied activation token not found")
            raise exc.InvalidTokenError()
        return ShowUser.model_validate(user)

    async def resend_activation_token(self, email: str) -> None:
        self._logger.info("Resend activation token request for %s", email)
        try:
            async with self._uow as uow:
                user = await uow.users_repo.get_by_email(email)
                await uow.tokens_repo.delete_all_for_user(
                    user.id, TokenScopes.ACTIVATION
                )
                plain_token, token_obj = self._statefull_token_provider.new_token(
                    user.id, self._activation_token_ttl, TokenScopes.ACTIVATION
                )
                await uow.tokens_repo.save(token_obj)
        except NotFoundError:
            self._logger.info("User with email: %s not found", email)
            raise exc.EntityNotFoundError(self.entity_name, email=email)
        if user.is_active:
            raise exc.UserAlreadyActivatedError()
        asyncio.create_task(
            self._mail_provider.send_mail_with_timeout(
                "Новый активационный токен",
                self._email_templates.new_activation_token(
                    plain_token, self._activation_link % plain_token
                ),
                user.email,
            )
        )
        self._logger.info("New activation token was succesfully send to %s", user.email)

    async def get_user_with_role(self, user_id: int) -> ShowUserWithRole:
        self._logger.info("Fetching user with role. id: %s", user_id)
        try:
            async with self._uow as uow:
                user, is_admin = await uow.users_repo.get_by_id_and_check_is_admin(
                    user_id
                )
        except NotFoundError:
            raise exc.EntityNotFoundError(self.entity_name, id=user_id)
        user.is_admin = is_admin
        return ShowUserWithRole.model_validate(user)

    async def check_is_user_admin(self, user_id: int) -> bool:
        async with self._uow as uow:
            return await uow.admins_repo.check_exists(user_id)
