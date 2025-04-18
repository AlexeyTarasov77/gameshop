import abc
from collections.abc import Callable
import typing as t
from logging import Logger

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.services.exceptions import ServiceError
from gateways.db.exceptions import DatabaseError, AbstractDatabaseExceptionMapper
from news.domain.interfaces import NewsRepositoryI
from news.repositories import NewsRepository
from orders.domain import interfaces as orders_i
from orders import repositories as orders_repos
from products.domain import interfaces as products_i
from products import repositories as products_repos
from users.domain import interfaces as users_i
from users import repositories as users_repos


class AcceptsSessionI(t.Protocol):
    def __init__(self, session): ...


class AbstractUnitOfWork[S](abc.ABC):
    exception_mapper: AbstractDatabaseExceptionMapper

    news_repo: NewsRepositoryI
    products_repo: products_i.ProductsRepositoryI
    products_prices_repo: products_i.PricesRepositoryI
    admins_repo: users_i.AdminsRepositoryI
    users_repo: users_i.UsersRepositoryI
    tokens_repo: users_i.TokensRepositoryI
    in_app_orders_repo: orders_i.InAppOrdersRepositoryI
    steam_top_up_repo: orders_i.SteamTopUpRepositoryI
    steam_gifts_repo: orders_i.SteamGiftsRepositoryI
    orders_repo: orders_i.AllOrdersRepositoryI

    def __init__(self, session_factory: Callable[[], S]):
        self._session_factory = session_factory
        self._session: S | None = None

    async def __aenter__(self) -> t.Self:
        self._session = self._session_factory()
        self._init_repos()
        return self

    @abc.abstractmethod
    def __call__(self) -> t.Self: ...

    async def __aexit__(self, exc_type, exc_value, _):
        await self.rollback()

    @abc.abstractmethod
    def _init_repos(self) -> None: ...

    def _register_repo[V: AcceptsSessionI](self, repo_cls: type[V]) -> V:
        assert self._session, "Attempt to register repos without initialized session"
        return repo_cls(self._session)

    @abc.abstractmethod
    async def commit(self) -> None: ...

    @abc.abstractmethod
    async def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork(AbstractUnitOfWork[AsyncSession]):
    def __init__(
        self,
        exception_mapper: AbstractDatabaseExceptionMapper,
        session_factory: Callable[[], AsyncSession],
        logger: Logger,
    ) -> None:
        self._logger = logger
        self.exception_mapper = exception_mapper
        super().__init__(session_factory)

    def _handle_exc(self, exc: Exception) -> t.NoReturn:
        if isinstance(exc, (DatabaseError, ServiceError)):
            raise exc
        self.exception_mapper.map_and_raise(getattr(exc, "orig", None) or exc)

    def __call__(self) -> t.Self:
        # create new instance to be able to share in async code
        self = self.__class__(
            self.exception_mapper, self._session_factory, self._logger
        )
        return self

    def _init_repos(self):
        # initializing repositories using created session
        self.users_repo = self._register_repo(users_repos.UsersRepository)
        self.admins_repo = self._register_repo(users_repos.AdminsRepository)
        self.products_prices_repo = self._register_repo(products_repos.PricesRepository)
        self.tokens_repo = self._register_repo(users_repos.TokensRepository)
        self.news_repo = self._register_repo(NewsRepository)
        self.products_repo = self._register_repo(products_repos.ProductsRepository)
        self.in_app_orders_repo = self._register_repo(
            orders_repos.InAppOrdersRepository
        )
        self.steam_top_up_repo = self._register_repo(orders_repos.SteamTopUpRepository)
        self.steam_gifts_repo = self._register_repo(orders_repos.SteamGiftsRepository)
        self.orders_repo = self._register_repo(orders_repos.OrdersRepository)
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
                self._logger.debug(
                    "SqlAlchemyUnitOfWork.__aexit__: exc: %s",
                    exc_value,
                    exc_info=True,
                )
                await super().__aexit__(exc_type, exc_value, _)
                self._handle_exc(exc_value)

            await self.commit()
        except SQLAlchemyError as e:
            self._logger.error("Exception during commiting/rollbacking trx", exc_info=e)
            self._handle_exc(e)
        finally:
            await self._session.close()

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()
