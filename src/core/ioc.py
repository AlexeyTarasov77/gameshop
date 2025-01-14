from pathlib import Path
from logging import Logger
import typing as t
from functools import lru_cache

import punq
from fastapi import Depends
from core.logger import setup_logger
from gateways.db.exceptions import PostgresExceptionsMapper
from gateways.db.main import SqlAlchemyDatabase
from news.domain.services import NewsService
from orders.domain.services import OrdersService
from products.domain.services import ProductsService
from users.domain.interfaces import HasherI, MailProviderI, TokenProviderI
from users.domain.services import UsersService
from users.hashing import BcryptHasher
from users.mailing import AsyncMailer
from users.tokens import JwtTokenProvider

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
    container.register(Logger, instance=logger)
    db = SqlAlchemyDatabase(
        str(cfg.storage_dsn),
        exception_mapper=PostgresExceptionsMapper,
        future=True,
    )
    container.register(HasherI, BcryptHasher)
    container.register(
        TokenProviderI,
        JwtTokenProvider,
        secret_key=cfg.jwt.secret,
        signing_alg=cfg.jwt.alg,
    )
    container.register(MailProviderI, AsyncMailer, **cfg.smtp.model_dump())
    container.register(SqlAlchemyDatabase, instance=db)
    container.register(Config, instance=cfg)
    container.register(
        AbstractUnitOfWork,
        SqlAlchemyUnitOfWork,
        session_factory=db.session_factory,
        logger=logger,
    )
    container.register(ProductsService, ProductsService)
    container.register(NewsService, NewsService)
    container.register(OrdersService, OrdersService)
    container.register(
        UsersService,
        UsersService,
        activation_token_ttl=cfg.jwt.activation_token_ttl,
        auth_token_ttl=cfg.jwt.auth_token_ttl,
        activation_link="http://localhost:8000/ping",
    )

    return container


def Inject[T](dep: t.Type[T]):  # noqa: N802
    def resolver() -> T:
        return t.cast(T, get_container().resolve(dep))

    return Depends(resolver)
