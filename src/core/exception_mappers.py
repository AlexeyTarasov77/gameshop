from collections.abc import Mapping
import logging
import abc
import typing as t

from fastapi.responses import JSONResponse
import gateways.db.exceptions as db_exc
from psycopg import errors as pg_exc
from core.services import exceptions as service_exc


from fastapi import FastAPI, Request, status


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


class HTTPExceptionsMapper:
    """Maps service errors to corresponding http status code"""

    _EXCEPTION_MAPPING: Mapping[type[Exception], int] = {
        service_exc.EntityNotFoundError: status.HTTP_404_NOT_FOUND,
        service_exc.EntityAlreadyExistsError: status.HTTP_409_CONFLICT,
        service_exc.EntityRelationshipNotFoundError: status.HTTP_400_BAD_REQUEST,
        service_exc.EntityOperationRestrictedByRefError: status.HTTP_403_FORBIDDEN,
        service_exc.UnavailableProductError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        service_exc.InvalidTokenError: status.HTTP_401_UNAUTHORIZED,
        service_exc.ExpiredTokenError: status.HTTP_401_UNAUTHORIZED,
        service_exc.InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
        service_exc.UserIsNotActivatedError: status.HTTP_403_FORBIDDEN,
        service_exc.UserAlreadyActivatedError: status.HTTP_403_FORBIDDEN,
    }

    def __init__(self, app: FastAPI):
        self._app = app

    async def _handle(self, _: Request, exc: Exception):
        status_code: int = self._EXCEPTION_MAPPING.get(
            type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        message: str = str(exc) if status_code < 500 else "Internal server error."
        return JSONResponse({"detail": message}, status_code)

    def setup_handlers(self) -> None:
        for exc_class in self._EXCEPTION_MAPPING:
            self._app.add_exception_handler(exc_class, self._handle)
        self._app.add_exception_handler(Exception, self._handle)


class AbstractDatabaseExceptionMapper[K: Exception](
    AbstractExceptionMapper[K, db_exc.DatabaseError]
): ...


class PostgresExceptionsMapper(AbstractDatabaseExceptionMapper[pg_exc.Error]):
    EXCEPTION_MAPPING: Mapping[type[pg_exc.Error], type[db_exc.DatabaseError]] = {
        pg_exc.NoData: db_exc.NotFoundError,
        pg_exc.UniqueViolation: db_exc.AlreadyExistsError,
    }

    def get_default_exc(self) -> type[db_exc.DatabaseError]:
        return db_exc.DatabaseError

    def map(self, exc: pg_exc.Error) -> type[db_exc.DatabaseError]:
        if isinstance(exc, pg_exc.ForeignKeyViolation):
            if "is still referenced" in str(exc):
                return db_exc.OperationRestrictedByRefError
            return db_exc.RelatedResourceNotFoundError
        return super().map(exc)

    def map_and_init(self, exc: pg_exc.Error) -> db_exc.DatabaseError:
        mapped_exc_cls = super().map(exc)
        return mapped_exc_cls(str(exc))
