from collections.abc import Mapping
import logging
import abc
import typing as t
import gateways.db.exceptions as db_exc
from psycopg import errors as pg_exc
from fastapi.exception_handlers import http_exception_handler


from fastapi import HTTPException, Request, status

from core.services.exceptions import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    EntityRelatedResourceNotFoundError,
    MappedServiceError,
)


class AbstractExceptionMapper[K: Exception, V: Exception](abc.ABC):
    EXCEPTION_MAPPING: Mapping[type[K], type[V]]

    @abc.abstractmethod
    def get_default_exc(self) -> type[V]: ...

    def map(self, exc: K) -> type[V]:
        exc_class = type(exc)
        mapped_exc_cls = self.EXCEPTION_MAPPING.get(t.cast(type[K], exc_class))
        if not mapped_exc_cls:
            logging.warning("Not mapped exception: %s", exc_class)
            return self.get_default_exc()
        return mapped_exc_cls

    @abc.abstractmethod
    def map_and_init(self, exc: K) -> V: ...

    def map_and_raise(self, exc: K) -> t.NoReturn:
        raise self.map_and_init(exc)


class HTTPInternalServerError(HTTPException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Internal server error"


class HTTPNotFoundException(HTTPDefaultException):
    status_code = status.HTTP_404_NOT_FOUND


class HTTPConflictException(HTTPDefaultException):
    status_code = status.HTTP_409_CONFLICT


class HTTPBadRequestException(HTTPDefaultException):
    status_code = status.HTTP_400_BAD_REQUEST


class HttpExceptionsMapper(
    AbstractExceptionMapper[MappedServiceError, HTTPDefaultException]
):
    """Maps service errors to corresponding http status code"""

    EXCEPTION_MAPPING: Mapping[type[MappedServiceError], type[HTTPDefaultException]] = {
        EntityNotFoundError: HTTPNotFoundException,
        EntityAlreadyExistsError: HTTPConflictException,
        EntityRelatedResourceNotFoundError: HTTPBadRequestException,
    }

    def get_default_exc(self):
        return HTTPDefaultException

    async def handle(self, _: Request, exc: Exception):
        if not isinstance(exc, MappedServiceError):
            return await http_exception_handler(_, self.get_default_exc()())
        mapped_exc_cls = super().map(exc)
        return await http_exception_handler(_, mapped_exc_cls(exc.msg))

    def map_and_init(self, exc: MappedServiceError) -> HTTPDefaultException:
        mapped_exc_cls = super().map(exc)
        return mapped_exc_cls(exc.msg)


class AbstractDatabaseExceptionMapper[K: Exception](
    AbstractExceptionMapper[K, db_exc.DatabaseError]
): ...


class PostgresExceptionsMapper(AbstractDatabaseExceptionMapper[pg_exc.Error]):
    EXCEPTION_MAPPING: Mapping[type[pg_exc.Error], type[db_exc.DatabaseError]] = {
        pg_exc.NoData: db_exc.NotFoundError,
        pg_exc.UniqueViolation: db_exc.AlreadyExistsError,
        pg_exc.ForeignKeyViolation: db_exc.RelatedResourceNotFoundError,
    }

    def get_default_exc(self) -> type[db_exc.DatabaseError]:
        return db_exc.DatabaseError

    def map_and_init(self, exc: pg_exc.Error) -> db_exc.DatabaseError:
        mapped_exc_cls = super().map(exc)
        return mapped_exc_cls(str(exc))


class ServiceExceptionMapper(
    AbstractExceptionMapper[db_exc.DatabaseError, MappedServiceError]
):
    def __init__(self, entity_name: str) -> None:
        self.entity_name = entity_name
        self.EXCEPTION_MAPPING: Mapping[
            type[db_exc.DatabaseError], type[MappedServiceError]
        ] = {
            db_exc.NotFoundError: EntityNotFoundError,
            db_exc.AlreadyExistsError: EntityAlreadyExistsError,
            db_exc.RelatedResourceNotFoundError: EntityRelatedResourceNotFoundError,
        }

    def get_default_exc(self) -> type[MappedServiceError]:
        return MappedServiceError

    def map_and_init(self, exc: db_exc.DatabaseError, **kwargs) -> MappedServiceError:
        mapped_exc_cls = super().map(exc)
        return mapped_exc_cls(self.entity_name, **kwargs)
