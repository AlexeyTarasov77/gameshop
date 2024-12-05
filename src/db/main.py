import logging
import typing as t

from psycopg import errors as pg_exc
from sqlalchemy import exc as sqla_exc
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


class DatabaseError(Exception): ...


class NotFoundError(DatabaseError): ...


class AlreadyExistsError(DatabaseError): ...


class RelatedResourceNotFoundError(DatabaseError): ...


# TODO: change to a abc/interface
class Database:
    EXCEPTION_MAPPING: dict[type[pg_exc.Error], type[DatabaseError]] = {
        pg_exc.UniqueViolation: AlreadyExistsError,
        pg_exc.ForeignKeyViolation: RelatedResourceNotFoundError,
    }

    def __init__(self, storage_dsn: str, **engine_params) -> None:
        self.engine = create_async_engine(storage_dsn, **engine_params)
        self.session_factory = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    @classmethod
    def map_sqla_exception(cls, exc: sqla_exc.SQLAlchemyError) -> DatabaseError:
        if isinstance(exc, sqla_exc.DBAPIError):
            pg_err_t = type(exc.orig)
            mapped_exc: type[DatabaseError] | None = cls.EXCEPTION_MAPPING.get(pg_err_t)
            if not mapped_exc:
                logging.warning("Not mapped exception: %s", pg_err_t)
                return DatabaseError
            return mapped_exc(str(exc))
        return exc

    @classmethod
    def raise_mapped_exc(cls, exc: Exception) -> t.NoReturn:
        raise cls.map_sqla_exception(exc)
