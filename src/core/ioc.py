import typing as t
from pathlib import Path

import punq
from core.db.main import Database
from core.uow import AbstractUnitOfWork, SqlAlchemyUnitOfWork
from fastapi import Depends, Request
from products.repositories import ProductsRepository

from config import Config


def init_container(cfg_path: str | Path) -> punq.Container:
    container = punq.Container()
    cfg = Config(yaml_file=cfg_path)
    db = Database(cfg.storage_dsn, future=True, echo=(cfg.mode == "local"))
    uow = SqlAlchemyUnitOfWork(db.session_factory, [ProductsRepository])
    container.register(Config, instance=cfg)
    container.register(AbstractUnitOfWork, instance=uow)

    return container


def Inject[T](dep: t.Type[T]) -> Depends:  # noqa: N802
    def resolver(req: Request) -> T:
        t.cast(punq.Container, req.app.state.ioc_container).resolve(dep)
    return Depends(resolver)
