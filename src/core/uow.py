import abc
from collections.abc import Callable
import typing as t
from logging import Logger

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.services.exceptions import ServiceError
from gateways.db.exceptions import DatabaseError, AbstractDatabaseExceptionMapper
from news.domain.interfaces import NewsRepositoryI
from news.repositories import NewsRepository
from orders.domain.interfaces import (
    OrderItemsRepositoryI,
    OrdersRepositoryI,
    SteamTopUpRepositoryI,
)
from orders.repositories import (
    OrderItemsRepository,
    OrdersRepository,
    SteamTopUpRepository,
)
from products.domain.interfaces import PricesRepositoryI, ProductsRepositoryI
from products.repositories import PricesRepository, ProductsRepository
from users.domain.interfaces import (
    AdminsRepositoryI,
    TokensRepositoryI,
    UsersRepositoryI,
)
from users.repositories import AdminsRepository, TokensRepository, UsersRepository


class AcceptsSessionI(t.Protocol):
    def __init__(self, session): ...


class AbstractUnitOfWork[S](abc.ABC):
    exception_mapper: AbstractDatabaseExceptionMapper

    news_repo: NewsRepositoryI
    products_repo: ProductsRepositoryI
    prices_repo: PricesRepositoryI
    admins_repo: AdminsRepositoryI
    users_repo: UsersRepositoryI
    tokens_repo: TokensRepositoryI
    orders_repo: OrdersRepositoryI
    order_items_repo: OrderItemsRepositoryI
    steam_top_up_repo: SteamTopUpRepositoryI

    def __init__(self, session_factory: Callable[[], S]):
        self._session_factory = session_factory
        self._session: S | None = None

    async def __aenter__(self) -> t.Self:
        self._session = self._session_factory()
        self._init_repos()
        return self

    async def __aexit__(self, exc_type, exc_value, _):
        await self.rollback()

    @abc.abstractmethod
    def _init_repos(self) -> None: ...

    def _register_repo[V: AcceptsSessionI](self, repo_cls: type[V]) -> V:
        assert self._session
        return repo_cls(self._session)

    @abc.abstractmethod
    async def commit(self) -> None: ...

    @abc.abstractmethod
    async def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork(AbstractUnitOfWork[AsyncSession]):
    def __init__(
        self,
        exception_mapper: AbstractDatabaseExceptionMapper,
        session_factory: async_sessionmaker[AsyncSession],
        logger: Logger,
    ) -> None:
        self.logger = logger
        self.exception_mapper = exception_mapper
        super().__init__(session_factory)

    def _handle_exc(self, exc: Exception) -> t.NoReturn:
        if isinstance(exc, (DatabaseError, ServiceError)):
            raise exc
        self.exception_mapper.map_and_raise(getattr(exc, "orig", None) or exc)

    async def __aenter__(self) -> t.Self:
        """Instantiating new session and initializing repos"""
        return await super().__aenter__()

    def _init_repos(self):
        # initializing repositories using created session
        self.users_repo = self._register_repo(UsersRepository)
        self.admins_repo = self._register_repo(AdminsRepository)
        self.prices_repo = self._register_repo(PricesRepository)
        self.tokens_repo = self._register_repo(TokensRepository)
        self.news_repo = self._register_repo(NewsRepository)
        self.products_repo = self._register_repo(ProductsRepository)
        self.orders_repo = self._register_repo(OrdersRepository)
        self.order_items_repo = self._register_repo(OrderItemsRepository)
        self.steam_top_up_repo = self._register_repo(SteamTopUpRepository)
        self._check_init_repos_correct()

    def _check_init_repos_correct(self):
        for name in self.__annotations__:
            if name.endswith("_repo"):
                assert name in self.__dict__

    async def __aexit__(self, exc_type, exc_value, _) -> None:
        """Commits/rollbacks transaction depending on whether exception occured"""
        assert self._session is not None
        try:
            if exc_type is not None:
                self.logger.debug(
                    "SqlAlchemyUnitOfWork.__aexit__: exc: %s",
                    exc_value,
                )
                await super().__aexit__(exc_type, exc_value, _)
                self._handle_exc(exc_value)

            await self.commit()
        except SQLAlchemyError as e:
            self.logger.error("Exception during commiting/rollbacking trx", exc_info=e)
            self._handle_exc(e)
        finally:
            await self._session.close()

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()
