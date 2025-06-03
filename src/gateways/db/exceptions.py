from core.exception_mappers import AbstractExceptionMapper
from collections.abc import Mapping
from psycopg import errors as pg_exc


class DatabaseError(Exception):
    def __init__(self, msg: str | None = None):
        self.msg = msg


class NotFoundError(DatabaseError): ...


class AlreadyExistsError(DatabaseError): ...


class ForeignKeyViolationError(DatabaseError): ...


class OperationRestrictedByRefError(ForeignKeyViolationError): ...


class RelatedResourceNotFoundError(ForeignKeyViolationError): ...


class AbstractDatabaseExceptionMapper[K: Exception](
    AbstractExceptionMapper[K, DatabaseError]
): ...


class PostgresExceptionsMapper(AbstractDatabaseExceptionMapper[pg_exc.Error]):
    EXCEPTION_MAPPING: Mapping[type[pg_exc.Error], type[DatabaseError]] = {
        pg_exc.NoData: NotFoundError,
        pg_exc.UniqueViolation: AlreadyExistsError,
    }

    def get_default_exc(self) -> type[DatabaseError]:
        return DatabaseError

    def map(self, exc: pg_exc.Error) -> type[DatabaseError]:
        if isinstance(exc, pg_exc.ForeignKeyViolation):
            if "is still referenced" in str(exc):
                return OperationRestrictedByRefError
            return RelatedResourceNotFoundError
        return super().map(exc)

    def map_and_init(self, exc: pg_exc.Error) -> DatabaseError:
        mapped_exc_cls = super().map(exc)
        return mapped_exc_cls(str(exc))
