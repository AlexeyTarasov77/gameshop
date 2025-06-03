from gateways.db.exceptions import AbstractDatabaseExceptionMapper
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


class SqlAlchemyClient:
    async def ping(self) -> None:
        # if db is not available - exception will be raised
        async with self._engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

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
