import typing as t
from functools import lru_cache

import punq
from db.main import Database
from fastapi import Depends
from products.domain.services import ProductsService
from products.repositories import ProductsRepository

from config import Config, init_config
from core.uow import AbstractUnitOfWork, SqlAlchemyUnitOfWork


@lru_cache(1)
def get_container() -> punq.Container:
    return _init_container()


def _init_container() -> punq.Container:
    container = punq.Container()
    cfg = init_config()
    db = Database(str(cfg.storage_dsn), future=True, echo=(cfg.mode == "local"))
    uow = SqlAlchemyUnitOfWork(db.session_factory, [ProductsRepository])
    container.register(Config, instance=cfg)
    container.register(AbstractUnitOfWork, instance=uow)
    container.register(ProductsService, ProductsService)

    return container


def Inject[T](dep: t.Type[T]) -> Depends:  # noqa: N802
    def resolver() -> T:
        return t.cast(punq.Container, get_container()).resolve(dep)
    return Depends(resolver)
