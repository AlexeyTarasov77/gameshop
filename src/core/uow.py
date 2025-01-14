import abc
import logging
import typing as t

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gateways.db.main import SqlAlchemyDatabase
from news.domain.interfaces import NewsRepositoryI
from orders.domain.interfaces import (
    OrderItemsRepositoryI,
    OrdersRepositoryI,
)
from products.domain.interfaces import (
    DeliveryMethodsRepositoryI,
    PlatformsRepositoryI,
    CategoriesRepositoryI,
    ProductsRepositoryI,
)
from users.domain.interfaces import UsersRepositoryI

logging.basicConfig(level=logging.DEBUG)


@t.runtime_checkable
class AcceptsSessionI(t.Protocol):
    def __init__(self, session: AsyncSession): ...


class AbstractUnitOfWork(abc.ABC):
    news_repo: NewsRepositoryI
    products_repo: ProductsRepositoryI
    delivery_methods_repo: DeliveryMethodsRepositoryI
    platforms_repo: PlatformsRepositoryI
    categories_repo: CategoriesRepositoryI
    users_repo: UsersRepositoryI
    orders_repo: OrdersRepositoryI
    order_items_repo: OrderItemsRepositoryI

    async def __aenter__(self) -> t.Self:
        return self

    async def __aexit__(self, exc_type, *args):
        await self.rollback()

    @abc.abstractmethod
    async def commit(self) -> None: ...

    @abc.abstractmethod
    async def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        logger: logging.Logger,
        news_repo_cls: type[NewsRepositoryI],
        products_repo_cls: type[ProductsRepositoryI],
        delivery_methods_repo_cls: type[DeliveryMethodsRepositoryI],
        platforms_repo_cls: type[PlatformsRepositoryI],
        categories_repo_cls: type[CategoriesRepositoryI],
        users_repo_cls: type[UsersRepositoryI],
        orders_repo_cls: type[OrdersRepositoryI],
        order_items_repo_cls: type[OrderItemsRepositoryI],
    ) -> None:
        self.session_factory = session_factory
        self.logger = logger
        self.session: AsyncSession | None = None
        self._news_repo_cls = news_repo_cls
        self._products_repo_cls = products_repo_cls
        self._delivery_methods_repo_cls = delivery_methods_repo_cls
        self._platforms_repo_cls = platforms_repo_cls
        self._categories_repo_cls = categories_repo_cls
        self._users_repo_cls = users_repo_cls
        self._orders_repo_cls = orders_repo_cls
        self._order_items_repo_cls = order_items_repo_cls

    def _handle_exc(self, exc: Exception) -> t.NoReturn:
        from core.ioc import get_container

        db = t.cast(SqlAlchemyDatabase, get_container().resolve(SqlAlchemyDatabase))
        db.exception_mapper.map_and_raise(getattr(exc, "orig", None) or exc)

    async def __aenter__(self) -> t.Self:
        self.session = self.session_factory()
        self._init_repos(self.session)
        return await super().__aenter__()

    def _init_repos(self, session: AsyncSession):
        # initializing repositories using created session
        for annotation_key in self.__annotations__.keys():
            if annotation_key.endswith("_repo"):
                repo_cls: type = getattr(self, f"_{annotation_key}_cls")
                if not issubclass(repo_cls, AcceptsSessionI):
                    raise ValueError(f"Invalid repository: {repo_cls.__name__}")
                setattr(self, annotation_key, repo_cls(session))

    async def __aexit__(self, exc_type, *args) -> None:
        assert self.session is not None
        try:
            if exc_type is not None:
                self.logger.error(
                    "SqlAlchemyUnitOfWork.__aexit__: exc: %s",
                    args[0],
                    exc_info=exc_type,
                )
                await super().__aexit__(exc_type, *args)
                self._handle_exc(args[0])

            self.logger.debug("commiting")
            await self.commit()
        except SQLAlchemyError as e:
            self.logger.error("Exception during commiting/rollbacking trx", exc_info=e)
            self._handle_exc(e)
        finally:
            self.logger.debug("closing session")
            await self.session.close()

    async def commit(self) -> None:
        assert self.session is not None
        await self.session.commit()

    async def rollback(self) -> None:
        assert self.session is not None
        await self.session.rollback()
