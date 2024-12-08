import typing as t
from functools import lru_cache

import punq
from fastapi import Depends

from config import Config, init_config
from core.uow import AbstractUnitOfWork, SqlAlchemyUnitOfWork
from gateways.db.exceptions import PostgresExceptionsMapper
from gateways.db.main import SqlAlchemyDatabase
from products.domain.services import ProductsService
from products.repositories import PlatformsRepository, ProductsRepository
from users.repositories import UsersRepository


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
        echo=(cfg.mode == "local"),
    )
    uow = SqlAlchemyUnitOfWork(
        db.session_factory, [ProductsRepository, PlatformsRepository, UsersRepository]
    )
    container.register(SqlAlchemyDatabase, instance=db)
    container.register(Config, instance=cfg)
    container.register(AbstractUnitOfWork, instance=uow)
    container.register(ProductsService, ProductsService)

    return container


def Inject[T](dep: t.Type[T]) -> Depends:  # noqa: N802
    def resolver() -> T:
        return t.cast(punq.Container, get_container()).resolve(dep)

    return Depends(resolver)
