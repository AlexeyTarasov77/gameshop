import abc
import logging
import typing as t

from db.repository import SqlAlchemyRepository
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.DEBUG)


class AbstractUnitOfWork(abc.ABC):
    async def __aenter__(self) -> t.Self:
        return self

    async def __aexit__(self, *args):
        await self.rollback()

    @abc.abstractmethod
    async def commit(self) -> None: ...

    @abc.abstractmethod
    async def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(
        self, session_factory: sessionmaker, repos_list: list[type[SqlAlchemyRepository]]
    ) -> None:
        self.session_factory: sessionmaker = session_factory
        self.session: AsyncSession | None = None
        self.repos_list = repos_list

    async def __aenter__(self) -> t.Self:
        self.session = self.session_factory()

        # initializing repositories using created session
        for repo in self.repos_list:
            setattr(self, repo.get_shortname(), repo(self.session))

        return await super().__aenter__()

    async def __aexit__(self, exc_type, *args):
        try:
            if exc_type is not None:
                logging.error("SqlAlchemyUnitOfWork.__aexit__: exc_type is not None", exc_info=exc_type)
                await super().__aexit__(exc_type, *args)
            else:
                logging.debug("commiting")
                await self.commit()
        except SQLAlchemyError as e:
            logging.error("Exception during commiting/rollbacking trx", exc_info=e)
            raise
        finally:
            await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
