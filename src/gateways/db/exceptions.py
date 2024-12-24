from collections.abc import Mapping
from functools import partial

from core.utils import AbstractExceptionMapper
from psycopg import errors as pg_exc


class DatabaseError(Exception): ...


class DBConnectionError(DatabaseError): ...


class NotFoundError(DatabaseError): ...


class AlreadyExistsError(DatabaseError): ...


class RelatedResourceNotFoundError(DatabaseError): ...


class AbstractDatabaseExceptionMapper[K: Exception](
    AbstractExceptionMapper[K, DatabaseError]
): ...


class PostgresExceptionsMapper(AbstractExceptionMapper[pg_exc.Error, DatabaseError]):
    EXCEPTION_MAPPING: Mapping[type[pg_exc.Error], type[DatabaseError]] = {
        pg_exc.NoData: NotFoundError,
        pg_exc.UniqueViolation: AlreadyExistsError,
        pg_exc.ForeignKeyViolation: RelatedResourceNotFoundError,
    }

    @classmethod
    def get_default_exc(cls) -> type[DatabaseError]:
        return DatabaseError

    @classmethod
    def map(cls, exc) -> partial[DatabaseError]:
        return partial(super().map(exc), str(exc))
