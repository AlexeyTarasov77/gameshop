import asyncio
import logging

from core.utils import Singleton
from gateways.db.exceptions import AbstractDatabaseExceptionMapper, DBConnectionError
from psycopg import OperationalError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


class SqlAlchemyDatabase(Singleton):
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
        exception_mapper: AbstractDatabaseExceptionMapper,
        **engine_params,
    ) -> None:
        self._dsn = storage_dsn
        self._engine = create_async_engine(storage_dsn, **engine_params)
        self.session_factory = sessionmaker(self._engine, class_=AsyncSession, expire_on_commit=False)
        self.exception_mapper = exception_mapper
        try:
            asyncio.run(self.ping())
        except RuntimeError as e:
            logging.error("Failed pinging database due to event loop issue", exc_info=e)
