from functools import partial

from core.exceptions import AbstractExceptionMapper
from psycopg import errors as pg_exc


class DatabaseError(Exception): ...


class NotFoundError(DatabaseError): ...


class AlreadyExistsError(DatabaseError): ...


class RelatedResourceNotFoundError(DatabaseError): ...


class AbstractDatabaseExceptionMapper[K: Exception](
    AbstractExceptionMapper[K, DatabaseError]
): ...


class PostgresExceptionsMapper(
    AbstractExceptionMapper[type[pg_exc.Error], type[DatabaseError]]
):
    EXCEPTION_MAPPING = {
        pg_exc.NoData: NotFoundError,
        pg_exc.UniqueViolation: AlreadyExistsError,
        pg_exc.ForeignKeyViolation: RelatedResourceNotFoundError,
    }

    @classmethod
    def get_default_exc(cls) -> type[DatabaseError]:
        return DatabaseError

    @classmethod
    def map(cls, exc) -> partial[type[DatabaseError]]:
        return partial(super().map(exc), str(exc))
