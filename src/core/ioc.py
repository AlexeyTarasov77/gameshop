import typing as t
from functools import lru_cache

import punq
from fastapi import Depends
from gateways.db.exceptions import PostgresExceptionsMapper
from gateways.db.main import SqlAlchemyDatabase
from news.domain.services import NewsService
from news.repositories import NewsRepository
from orders.domain.services import OrdersService
from orders.repositories import OrdersRepository, OrderItemsRepository
from products.domain.services import ProductsService
from products.repositories import (
    CategoriesRepository,
    PlatformsRepository,
    DeliveryMethodsRepository,
    ProductsRepository,
)
from users.domain.interfaces import HasherI, MailProviderI, TokenProviderI
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
        products_repo_cls=ProductsRepository,
        delivery_methods_repo_cls=DeliveryMethodsRepository,
        platforms_repo_cls=PlatformsRepository,
        categories_repo_cls=CategoriesRepository,
        users_repo_cls=UsersRepository,
        news_repo_cls=NewsRepository,
        orders_repo_cls=OrdersRepository,
        order_items_repo_cls=OrderItemsRepository,
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
    container.register(AbstractUnitOfWork, instance=uow)
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
