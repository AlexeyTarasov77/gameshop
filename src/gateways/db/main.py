from core.exception_mappers import AbstractDatabaseExceptionMapper
from gateways.db.exceptions import DBConnectionError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


class SqlAlchemyDatabase:
    async def ping(self) -> None:
        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        except OperationalError as e:
            raise DBConnectionError(
                """Connection failed: unable to connect to: '%s' ,
                Make sure your storage is available under specified dsn"""
                % self._dsn
            ) from e

    def __init__(
        self,
        storage_dsn: str,
        exception_mapper: type[AbstractDatabaseExceptionMapper],
        **engine_params,
    ) -> None:
        self._dsn = storage_dsn
        self._engine = create_async_engine(storage_dsn, **engine_params)
        # used in synchronous tests
        self.sync_engine = create_engine(storage_dsn)
        self.session_factory = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self.exception_mapper = exception_mapper
