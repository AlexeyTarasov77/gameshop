import typing as t
from functools import lru_cache

import punq
from fastapi import Depends
from gateways.db.exceptions import PostgresExceptionsMapper
from gateways.db.main import SqlAlchemyDatabase
from products.domain.services import ProductsService
from products.repositories import (
    CategoriesRepository,
    PlatformsRepository,
    ProductsRepository,
)
from users.domain.services import UsersService
from users.hashing import BcryptHasher
from users.mailing import AsyncMailer
from users.repositories import UsersRepository
from users.tokens import JwtTokenProvider

from config import Config, init_config
from core.uow import AbstractUnitOfWork, SqlAlchemyUnitOfWork


@lru_cache(1)
def get_container() -> punq.Container:
    return _init_container()


def _init_container() -> punq.Container:
    container = punq.Container()
    cfg = init_config()
    db = SqlAlchemyDatabase(
        str(cfg.storage_dsn),
        exception_mapper=PostgresExceptionsMapper,
        future=True,
        echo=cfg.debug,
    )
    uow = SqlAlchemyUnitOfWork(
        db.session_factory,
        [ProductsRepository, PlatformsRepository, CategoriesRepository, UsersRepository],
    )
    hasher = BcryptHasher()
    mail_provider = AsyncMailer(**cfg.smtp.model_dump())
    token_provider = JwtTokenProvider(secret_key=cfg.jwt.secret, signing_alg=cfg.jwt.alg)
    container.register(SqlAlchemyDatabase, instance=db)
    container.register(Config, instance=cfg)
    container.register(AbstractUnitOfWork, instance=uow)
    container.register(ProductsService, ProductsService)
    container.register(
        UsersService,
        UsersService,
        hasher=hasher,
        mail_provider=mail_provider,
        token_provider=token_provider,
        activation_token_ttl=cfg.jwt.activation_token_ttl,
        activation_link="http://localhost:8000/ping",
    )

    return container


def Inject[T](dep: t.Type[T]) -> Depends:  # noqa: N802
    def resolver() -> T:
        return t.cast(punq.Container, get_container()).resolve(dep)

    return Depends(resolver)
