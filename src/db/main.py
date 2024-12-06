from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db.exceptions import AbstractDatabaseExceptionMapper


# TODO: change to a abc/interface
class Database:
    def __init__(
        self,
        storage_dsn: str,
        exception_mapper: AbstractDatabaseExceptionMapper,
        **engine_params,
    ) -> None:
        self._engine = create_async_engine(storage_dsn, **engine_params)
        self.session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self.exception_mapper = exception_mapper
        # TODO: add db pinging to verify conn
