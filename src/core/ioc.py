from pathlib import Path
from logging import Logger
import typing as t
from functools import lru_cache

from httpx import AsyncClient
import punq
from fastapi import Depends
from core.tasks import BackgroundJobs
from mailing.domain.services import MailingService
from orders.repositories import TopUpFeeManager
from payments.domain.interfaces import (
    EmailTemplatesI as PaymentEmailTemplatesI,
    PaymentSystemFactoryI,
    TelegramClientI,
)
from payments.domain.services import PaymentsService
from payments.payment_gateways import PaymentSystemFactoryImpl
from products.domain.interfaces import CurrencyConverterI
from gateways.steam import GamesForFarmAPIClient, NSGiftsAPIClient
from gateways.currency_converter import CurrencyConverter
from shopping.domain.interfaces import (
    CartManagerFactoryI,
    SessionCopierI,
    WishlistManagerFactoryI,
)
from shopping.domain.services import ShoppingService
from shopping.repositories import (
    CartManagerFactory,
    SessionCopier,
    WishlistManagerFactory,
)
from core.logger import setup_logger
from core.exception_mappers import HTTPExceptionsMapper
from gateways.db.exceptions import (
    AbstractDatabaseExceptionMapper,
    PostgresExceptionsMapper,
)
from shopping.sessions import RedisSessionCreator, RedisSessionManager, SessionCreatorI
from gateways.db import SqlAlchemyClient, RedisClient
from gateways.tg_client import TelegramClient
from news.domain.services import NewsService
from orders.domain.services import OrdersService
from orders.domain.interfaces import SteamAPIClientI, TopUpFeeManagerI
from products.domain.services import ProductsService
from users.domain.interfaces import (
    EmailTemplatesI as UsersEmailTemplatesI,
    PasswordHasherI,
    StatefullTokenProviderI,
    TokenHasherI,
    StatelessTokenProviderI,
)
from users.domain.services import UsersService
from users.hashing import BcryptHasher, SHA256Hasher
from users.tokens import JwtTokenProvider, SecureTokenProvider
from mailing.templates import EmailTemplates
from config import Config, init_config
from core.uow import AbstractUnitOfWork, SqlAlchemyUnitOfWork


@lru_cache(1)
def get_container() -> punq.Container:
    return _init_container()


class SupportsAsyncClose(t.Protocol):
    async def aclose(self): ...


cleanup_list: list[SupportsAsyncClose] = []


def register_for_cleanup(obj: SupportsAsyncClose):
    cleanup_list.append(obj)


def _init_container() -> punq.Container:
    container = punq.Container()
    cfg = init_config()
    logger = setup_logger(
        cfg.debug, (Path().parent.parent / "logs" / "errors.log").as_posix()
    )
    FRONTEND_DOMAIN = "http://localhost:3000" if cfg.debug else "https://gamebazaar.ru"
    container.register("FRONTEND_DOMAIN", instance=FRONTEND_DOMAIN)
    redis_client = RedisClient.from_url(str(cfg.redis_dsn))
    httpx_client = AsyncClient()
    register_for_cleanup(redis_client)  # type: ignore
    register_for_cleanup(httpx_client)
    container.register(Logger, instance=logger)
    container.register(AsyncClient, instance=httpx_client)
    container.register(AbstractDatabaseExceptionMapper, PostgresExceptionsMapper)
    container.register(RedisSessionManager, RedisSessionManager)
    container.register(HTTPExceptionsMapper, HTTPExceptionsMapper)
    container.register(RedisClient, instance=redis_client)
    db = SqlAlchemyClient(
        str(cfg.pg_dsn), exception_mapper=PostgresExceptionsMapper, future=True
    )
    container.register(PasswordHasherI, BcryptHasher)
    container.register(TokenHasherI, SHA256Hasher)
    container.register(
        StatelessTokenProviderI,
        JwtTokenProvider,
        secret_key=cfg.tokens.secret,
        signing_alg=cfg.tokens.alg,
    )
    container.register(StatefullTokenProviderI, SecureTokenProvider)
    container.register(
        MailingService, scope=punq.Scope.singleton, **cfg.smtp.model_dump()
    )
    container.register(SqlAlchemyClient, instance=db)
    container.register(Config, instance=cfg)
    container.register(
        AbstractUnitOfWork,
        SqlAlchemyUnitOfWork,
        session_factory=db.session_factory,
    )
    container.register(UsersEmailTemplatesI, EmailTemplates)
    container.register(TelegramClientI, TelegramClient, token=cfg.clients.tg_api.token)
    container.register(PaymentEmailTemplatesI, EmailTemplates)
    container.register(ProductsService, scope=punq.Scope.singleton)
    container.register(NewsService, scope=punq.Scope.singleton)
    container.register(TopUpFeeManagerI, TopUpFeeManager)
    container.register(
        OrdersService,
        scope=punq.Scope.singleton,
    )
    container.register(
        UsersService,
        UsersService,
        scope=punq.Scope.singleton,
        activation_token_ttl=cfg.tokens.activation_token_ttl,
        auth_token_ttl=cfg.tokens.auth_token_ttl,
        password_reset_token_ttl=cfg.tokens.password_reset_token_ttl,
        email_verification_token_ttl=cfg.tokens.email_verification_token_ttl,
        activation_link_builder=lambda token: f"{FRONTEND_DOMAIN}/auth/activate?token={token}",
        password_reset_link_builder=lambda token: f"{FRONTEND_DOMAIN}/auth/password-update?token={token}",
        email_verification_link_builder=lambda token: f"{FRONTEND_DOMAIN}/auth/verify-email?token={token}",
    )
    container.register(CartManagerFactoryI, CartManagerFactory)
    container.register(WishlistManagerFactoryI, WishlistManagerFactory)
    container.register(SessionCopierI, SessionCopier)
    container.register(CurrencyConverterI, CurrencyConverter)
    container.register(ShoppingService, scope=punq.Scope.singleton)
    container.register(
        PaymentsService,
        scope=punq.Scope.singleton,
        order_details_link_builder=lambda order_id: f"{FRONTEND_DOMAIN}/orderhistory/{order_id}",
        admin_tg_chat_id=cfg.clients.tg_api.admin_chat_id,
    )
    container.register(
        SteamAPIClientI,
        NSGiftsAPIClient,
        steam_api_auth_email=cfg.clients.steam_api.auth_email,
        steam_api_auth_password=cfg.clients.steam_api.auth_password,
        scope=punq.Scope.singleton,
    )
    container.register(PaymentSystemFactoryI, PaymentSystemFactoryImpl)
    container.register(GamesForFarmAPIClient, GamesForFarmAPIClient)
    container.register(
        SessionCreatorI, RedisSessionCreator, ttl=cfg.server.sessions.ttl
    )
    container.register(BackgroundJobs, BackgroundJobs)
    return container


def Resolve[T](dep: type[T] | str, **kwargs) -> T:
    return t.cast(T, get_container().resolve(dep, **kwargs))


def Inject[T](dep: type[T] | str, **kwargs):
    def resolver() -> T:
        return Resolve(dep, **kwargs)

    return Depends(resolver)
