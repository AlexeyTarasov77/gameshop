import asyncio
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from core.logging import AbstractLogger
from typing import cast

from jwt.exceptions import InvalidTokenError as InvalidJwtTokenError

from core.services.base import BaseService
from core.services import exceptions as exc
from core.uow import AbstractUnitOfWork
from core.utils import UnspecifiedType
from gateways.db.exceptions import AlreadyExistsError, NotFoundError

from mailing.domain.services import MailingService
from shopping.domain.interfaces import SessionCopierI
from users.domain.interfaces import (
    EmailTemplatesI,
    PasswordHasherI,
    StatefullTokenProviderI,
    TokenHasherI,
    StatelessTokenProviderI,
    TokensRepositoryI,
)
from users.models import TokenScopes
from users.schemas import (
    CreateUserDTO,
    ShowUser,
    ShowUserWithRole,
    UpdateUserDTO,
    UserSignInDTO,
)


class UsersService(BaseService):
    entity_name = "User"
    type LinkWithTokenBuilder = Callable[[str], str]

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        logger: AbstractLogger,
        email_templates: EmailTemplatesI,
        token_hasher: TokenHasherI,
        password_hasher: PasswordHasherI,
        jwt_token_provider: StatelessTokenProviderI,
        statefull_token_provider: StatefullTokenProviderI,
        mailing_service: MailingService,
        session_copier: SessionCopierI,
        activation_token_ttl: timedelta,
        auth_token_ttl: timedelta,
        password_reset_token_ttl: timedelta,
        email_verification_token_ttl: timedelta,
        activation_link_builder: LinkWithTokenBuilder,
        password_reset_link_builder: LinkWithTokenBuilder,
        email_verification_link_builder: LinkWithTokenBuilder,
    ) -> None:
        super().__init__(uow, logger)
        self._password_hasher = password_hasher
        self._token_hasher = token_hasher
        self._jwt_token_provider = jwt_token_provider
        self._session_copier = session_copier
        self._statefull_token_provider = statefull_token_provider
        self._mailing_service = mailing_service
        self._activation_link_builder = activation_link_builder
        self._password_reset_link_builder = password_reset_link_builder
        self._email_verification_link_builder = email_verification_link_builder
        self._activation_token_ttl = activation_token_ttl
        self._password_reset_token_ttl = password_reset_token_ttl
        self._email_verification_token_ttl = email_verification_token_ttl
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
        self._logger.info("Start user signup", email=dto.email)
        password_hash = self._password_hasher.hash(dto.password)
        try:
            async with self._uow() as uow:
                user = await uow.users_repo.create_with_hashed_password(
                    dto, password_hash, cast(str | None, dto.photo)
                )
                # deliberately creating token inside transaction to avoid user creating in case of error
                plain_token = await self._create_and_save_token(
                    user.id,
                    TokenScopes.ACTIVATION,
                    uow.tokens_repo,
                )
        except AlreadyExistsError:
            self._logger.info("User already exists", email=dto.email)
            # if user already exists but not activated yet - resend activation token
            try:
                await self.resend_activation_token(dto.email)
            except exc.UserAlreadyActivatedError:
                pass
            else:
                raise exc.UserIsNotActivatedError(
                    "Your account already exists but not activated yet, we've sent a new activation token on your email. Activate your account and sign in"
                )
            raise exc.EntityAlreadyExistsError(self.entity_name, email=dto.email)
        email_body = await self._email_templates.signup(
            user.username, self._activation_link_builder(plain_token)
        )
        asyncio.create_task(
            self._mailing_service.send_mail(
                "Аккаунт успешно создан",
                email_body,
                user.email,
            )
        )
        self._logger.info(
            "Succefully signed up user and sent confirmation token.",
            user_id=user.id,
            token_destination=user.email,
        )
        return ShowUser.model_validate(user)

    async def signin(self, dto: UserSignInDTO, session_key: str) -> str:
        self._logger.info("Signing in user", email=dto.email)
        try:
            async with self._uow() as uow:
                user = await uow.users_repo.get_by_email(dto.email)
        except NotFoundError as e:
            self._logger.warning("User with provided email not found", email=dto.email)
            raise exc.InvalidCredentialsError() from e
        if not user.is_active:
            self._logger.warning(
                "Attempt to sign in from not activated user", user_id=user.id
            )
            raise exc.UserIsNotActivatedError("Activate account to sign in")
        if not self._password_hasher.compare(dto.password, user.password_hash):
            self._logger.info("Passwords does not match", user_id=user.id)
            raise exc.InvalidCredentialsError()
        token = self._jwt_token_provider.new_token(
            {"uid": user.id}, self._auth_token_ttl
        )
        await self._session_copier.copy_for_user(session_key, user.id)
        self._logger.info("User succesfully signed in", user_id=user.id)
        return token

    async def send_password_reset_token(self, user_email: str):
        self._logger.info("Processing password reset request", user_email=user_email)
        try:
            async with self._uow() as uow:
                user = await uow.users_repo.get_by_email(user_email)
                plain_token, token_obj = self._statefull_token_provider.new_token(
                    user.id, self._password_reset_token_ttl, TokenScopes.PASSWORD_RESET
                )
                await uow.tokens_repo.save(token_obj)
        except NotFoundError:
            self._logger.info("User not found by email", email=user_email)
            raise exc.EntityNotFoundError(self.entity_name, email=user_email)
        email_body = await self._email_templates.password_reset(
            user.username, self._password_reset_link_builder(plain_token)
        )
        asyncio.create_task(
            self._mailing_service.send_mail(
                "Сброс пароля",
                email_body,
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
            async with self._uow() as uow:
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
        self._logger.info("Password succesfully updated", user_id=token.user_id)

    def verify_token_and_get_payload(self, token: str) -> Mapping:
        try:
            token_payload = self._jwt_token_provider.extract_payload(token)
            token_exp = datetime.fromtimestamp(token_payload["exp"])
        except (InvalidJwtTokenError, KeyError) as e:
            raise exc.InvalidTokenError() from e
        if token_exp < datetime.now():
            raise exc.ExpiredTokenError()
        return token_payload

    async def extract_and_validate_user_id_from_token(self, token: str) -> int:
        payload = self.verify_token_and_get_payload(token)
        user_id = payload.get("uid", -1)
        try:
            if int(user_id) < 1:
                raise ValueError()
        except ValueError:  # user_id is not a valid digit or < 1
            raise exc.InvalidTokenError()
        async with self._uow() as uow:
            is_valid = await uow.users_repo.check_exists_active(user_id)
        if not is_valid:
            self._logger.warning(
                "User associated with provided auth token does not exist"
            )
            raise exc.InvalidTokenError()
        return user_id

    async def update_user(
        self, dto: UpdateUserDTO, user_id: int
    ) -> tuple[ShowUser, bool]:
        photo_url: str | None | UnspecifiedType = ...
        if "photo_url" in dto.model_fields_set:
            photo_url = cast(str | None, dto.photo)
        async with self._uow() as uow:
            user = await uow.users_repo.update_by_id(
                user_id, username=dto.username, photo_url=photo_url
            )
        verification_email_sent = False
        if dto.email is not None:
            self._logger.info(
                "Updating user's email which requires confirmation", user_id=user_id
            )
            token = self._jwt_token_provider.new_token(
                {"email": dto.email, "uid": user_id},
                self._email_verification_token_ttl,
            )
            email_body = await self._email_templates.email_verification(
                user.username, self._email_verification_link_builder(token)
            )
            asyncio.create_task(
                self._mailing_service.send_mail(
                    "Подтверждение обновления email'a",
                    email_body,
                    dto.email,
                )
            )
            verification_email_sent = True
        return ShowUser.model_validate(user), verification_email_sent

    async def update_email_confirm(self, curr_user_id: int, token: str) -> ShowUser:
        payload = self.verify_token_and_get_payload(token)
        new_email = payload.get("email")
        user_id_from_token = payload.get("uid")
        if not user_id_from_token or not new_email:
            self._logger.info("Malformed jwt token for email confirmation", token=token)
            raise exc.InvalidTokenError()
        if curr_user_id != user_id_from_token:
            self._logger.warning(
                "User tries to update email of another user",
                curr_user_id=curr_user_id,
                orig_user_id=user_id_from_token,
            )
            raise exc.ActionForbiddenError()
        async with self._uow() as uow:
            user = await uow.users_repo.update_by_id(
                user_id_from_token, email=new_email
            )
        return ShowUser.model_validate(user)

    async def activate_user(self, plain_token: str) -> ShowUser:
        self._logger.info("Activating user")
        token_hash = await asyncio.to_thread(self._token_hasher.hash, plain_token)
        try:
            async with self._uow() as uow:
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
        self._logger.info("Processing resend activation token request", email=email)
        try:
            async with self._uow() as uow:
                user = await uow.users_repo.get_by_email(email)
                if user.is_active:
                    raise exc.UserAlreadyActivatedError()
                await uow.tokens_repo.delete_all_for_user(
                    user.id, TokenScopes.ACTIVATION
                )
                plain_token, token_obj = self._statefull_token_provider.new_token(
                    user.id, self._activation_token_ttl, TokenScopes.ACTIVATION
                )
                await uow.tokens_repo.save(token_obj)
        except NotFoundError:
            self._logger.info("User not found by email", email=email)
            raise exc.EntityNotFoundError(self.entity_name, email=email)
        email_body = await self._email_templates.new_activation_token(
            user.username, plain_token, self._activation_link_builder(plain_token)
        )
        asyncio.create_task(
            self._mailing_service.send_mail(
                "Новый активационный токен",
                email_body,
                user.email,
            )
        )
        self._logger.info(
            "New activation token was succesfully sent", token_destination=user.email
        )

    async def get_user_with_role(self, user_id: int) -> ShowUserWithRole:
        self._logger.info("Fetching user with role", id=user_id)
        try:
            async with self._uow() as uow:
                user, is_admin = await uow.users_repo.get_by_id_and_check_is_admin(
                    user_id
                )
        except NotFoundError:
            raise exc.EntityNotFoundError(self.entity_name, id=user_id)
        user.is_admin = is_admin
        return ShowUserWithRole.model_validate(user)

    async def check_is_user_admin(self, user_id: int) -> bool:
        async with self._uow() as uow:
            return await uow.admins_repo.check_exists(user_id)
