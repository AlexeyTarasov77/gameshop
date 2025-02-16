from pathlib import Path
from logging import Logger
import typing as t
from functools import lru_cache

import punq
from fastapi import Depends
from redis.asyncio import Redis
from sessions.domain.interfaces import CartManagerFactoryI, WishlistManagerFactoryI
from sessions.domain.services import SessionsService
from sessions.repositories import (
    CartSessionManager,
    WishlistSessionManager,
    cart_manager_factory,
    wishlist_manager_factory,
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
    MailProviderI,
    PasswordHasherI,
    StatefullTokenProviderI,
    TokenHasherI,
    StatelessTokenProviderI,
)
from users.domain.services import UsersService
from users.hashing import BcryptHasher, SHA256Hasher
from users.mailing import AsyncMailer
from users.tokens import JwtTokenProvider, SecureTokenProvider

from config import Config, init_config
from core.uow import AbstractUnitOfWork, SqlAlchemyUnitOfWork


@lru_cache(1)
def get_container() -> punq.Container:
    return _init_container()


def _init_container() -> punq.Container:
    FRONTEND_URL = "http://localhost:3000"
    container = punq.Container()
    cfg = init_config()
    logger = setup_logger(
        cfg.debug, (Path().parent.parent / "logs" / "errors.log").as_posix()
    )
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
        secret_key=cfg.jwt.secret,
        signing_alg=cfg.jwt.alg,
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
    container.register(ProductsService, ProductsService)
    container.register(NewsService, NewsService)
    container.register(
        OrdersService, OrdersService, order_details_link=f"{FRONTEND_URL}/orders/%s"
    )
    container.register(
        UsersService,
        UsersService,
        activation_token_ttl=cfg.jwt.activation_token_ttl,
        auth_token_ttl=cfg.jwt.auth_token_ttl,
        activation_link=f"{FRONTEND_URL}/auth/activate?token=%s",
    )
    container.register(CartManagerFactoryI, cart_manager_factory, db=redis)
    container.register(WishlistManagerFactoryI, wishlist_manager_factory, db=redis)
    container.register(SessionsService)
    container.register(
        SessionCreatorI, RedisSessionCreator, ttl=cfg.server.sessions.ttl
    )

    return container


def Resolve[T](dep: type[T], **kwargs) -> T:
    return t.cast(T, get_container().resolve(dep, **kwargs))


def Inject[T](dep: type[T], **kwargs):
    def resolver() -> T:
        return Resolve(dep, **kwargs)

    return Depends(resolver)
