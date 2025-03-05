from pathlib import Path
from logging import Logger
import typing as t
from functools import lru_cache

import punq
from fastapi import Depends
from redis.asyncio import Redis
from payments.domain.interfaces import PaymentEmailTemplatesI, PaymentSystemFactoryI
from payments.domain.services import PaymentsService
from payments.systems import PaymentSystemFactoryImpl
from sessions.domain.interfaces import (
    CartManagerFactoryI,
    SessionCopierI,
    WishlistManagerFactoryI,
)
from sessions.domain.services import SessionsService
from sessions.repositories import (
    CartManagerFactory,
    SessionCopier,
    WishlistManagerFactory,
)
from core.logger import setup_logger
from core.exception_mappers import (
    AbstractDatabaseExceptionMapper,
    HTTPExceptionsMapper,
    PostgresExceptionsMapper,
)
from sessions.sessions import RedisSessionCreator, RedisSessionManager, SessionCreatorI
from gateways.db.main import SqlAlchemyDatabase
from gateways.redis.main import init_redis_client
from news.domain.services import NewsService
from orders.domain.services import OrdersService
from products.domain.services import ProductsService
from users.domain.interfaces import (
    UserEmailTemplatesI,
    MailProviderI,
    PasswordHasherI,
    StatefullTokenProviderI,
    TokenHasherI,
    StatelessTokenProviderI,
)
from users.domain.services import UsersService
from users.hashing import BcryptHasher, SHA256Hasher
from users.mailing import AsyncMailer, EmailTemplates
from users.tokens import JwtTokenProvider, SecureTokenProvider

from config import Config, init_config
from core.uow import AbstractUnitOfWork, SqlAlchemyUnitOfWork


@lru_cache(1)
def get_container() -> punq.Container:
    return _init_container()


def _init_container() -> punq.Container:
    container = punq.Container()
    cfg = init_config()
    logger = setup_logger(
        cfg.debug, (Path().parent.parent / "logs" / "errors.log").as_posix()
    )
    FRONTEND_DOMAIN = "http://localhost:3000" if cfg.debug else "https://gamebazaar.ru"
    container.register("FRONTEND_DOMAIN", instance=FRONTEND_DOMAIN)
    redis = init_redis_client(str(cfg.redis_dsn))
    container.register(Logger, instance=logger)
    container.register(AbstractDatabaseExceptionMapper, PostgresExceptionsMapper)
    container.register(RedisSessionManager, RedisSessionManager)
    container.register(HTTPExceptionsMapper, HTTPExceptionsMapper)
    container.register(Redis, instance=redis)
    db = SqlAlchemyDatabase(
        str(cfg.pg_dsn),
        exception_mapper=PostgresExceptionsMapper,
        future=True,
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
    container.register(MailProviderI, AsyncMailer, **cfg.smtp.model_dump())
    container.register(SqlAlchemyDatabase, instance=db)
    container.register(Config, instance=cfg)
    container.register(
        AbstractUnitOfWork,
        SqlAlchemyUnitOfWork,
        session_factory=db.session_factory,
    )
    container.register(UserEmailTemplatesI, EmailTemplates)
    container.register(PaymentEmailTemplatesI, EmailTemplates)
    container.register(ProductsService)
    container.register(NewsService)
    container.register(OrdersService)
    container.register(
        UsersService,
        UsersService,
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
    container.register(SessionsService)
    container.register(
        PaymentsService,
        PaymentsService,
        order_details_link_builder=lambda order_id: f"{FRONTEND_DOMAIN}/orderhistory/{order_id}",
    )
    container.register(PaymentSystemFactoryI, PaymentSystemFactoryImpl)
    container.register(
        SessionCreatorI, RedisSessionCreator, ttl=cfg.server.sessions.ttl
    )

    return container


def Resolve[T](dep: type[T] | str, **kwargs) -> T:
    return t.cast(T, get_container().resolve(dep, **kwargs))


def Inject[T](dep: type[T] | str, **kwargs):
    def resolver() -> T:
        return Resolve(dep, **kwargs)

    return Depends(resolver)
