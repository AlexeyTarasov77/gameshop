from collections.abc import Mapping
import logging
import abc
import typing as t
from functools import partial
from http import HTTPStatus
import gateways.db.exceptions as db_exc
from psycopg import errors as pg_exc


from fastapi import HTTPException

from core.services.exceptions import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    EntityRelatedResourceNotFoundError,
    ServiceError,
)


class AbstractExceptionMapper[K: Exception, V: Exception](abc.ABC):
    EXCEPTION_MAPPING: Mapping[type[K], type[V]]

    @classmethod
    @abc.abstractmethod
    def get_default_exc(cls) -> type[V]: ...

    @classmethod
    def map(cls, exc: K | V) -> type[V] | partial[V]:
        exc_class = type(exc)
        if exc_class in cls.EXCEPTION_MAPPING.values():
            return t.cast(type[V], exc_class)
        mapped_exc_class = cls.EXCEPTION_MAPPING.get(t.cast(type[K], exc_class))
        if not mapped_exc_class:
            logging.warning("Not mapped exception: %s", exc_class)
            return cls.get_default_exc()
        return mapped_exc_class

    @classmethod
    def map_and_raise(cls, exc: K) -> t.NoReturn:
        mapped = cls.map(exc)
        raise mapped()


class HttpExceptionsMapper(AbstractExceptionMapper[ServiceError, HTTPException]):
    """Maps service errors to corresponding http status code"""

    EXCEPTION_MAPPING: Mapping[type[ServiceError], partial[HTTPException]] = {
        EntityNotFoundError: partial(HTTPException, status_code=HTTPStatus.NOT_FOUND),
        EntityAlreadyExistsError: partial(
            HTTPException, status_code=HTTPStatus.CONFLICT
        ),
        EntityRelatedResourceNotFoundError: partial(
            HTTPException, status_code=HTTPStatus.BAD_REQUEST
        ),
    }

    @classmethod
    def get_default_exc(cls):
        return partial(HTTPException, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    @classmethod
    def map(cls, exc):
        mapped_exc_class = super().map(exc)
        return partial(mapped_exc_class, detail=exc.msg)


class AbstractDatabaseExceptionMapper[K: Exception](
    AbstractExceptionMapper[K, db_exc.DatabaseError]
): ...


class PostgresExceptionsMapper(AbstractDatabaseExceptionMapper[pg_exc.Error]):
    EXCEPTION_MAPPING: Mapping[type[pg_exc.Error], type[db_exc.DatabaseError]] = {
        pg_exc.NoData: db_exc.NotFoundError,
        pg_exc.UniqueViolation: db_exc.AlreadyExistsError,
        pg_exc.ForeignKeyViolation: db_exc.RelatedResourceNotFoundError,
    }

    @classmethod
    def get_default_exc(cls) -> type[db_exc.DatabaseError]:
        return db_exc.DatabaseError

    @classmethod
    def map(cls, exc) -> partial[db_exc.DatabaseError]:
        return partial(super().map(exc), str(exc))


class ServiceExceptionMapper(
    AbstractExceptionMapper[db_exc.DatabaseError, ServiceError]
):
    def __init__(self, entity_name: str | None = None) -> None:
        self.entity_name = entity_name

    EXCEPTION_MAPPING: Mapping[type[db_exc.DatabaseError], type[ServiceError]] = {
        db_exc.NotFoundError: EntityNotFoundError,
        db_exc.AlreadyExistsError: EntityAlreadyExistsError,
        db_exc.RelatedResourceNotFoundError: EntityRelatedResourceNotFoundError,
    }

    @classmethod
    def get_default_exc(cls) -> type[ServiceError]:
        return ServiceError

    def map_with_entity(self, exc: db_exc.DatabaseError) -> partial[ServiceError]:
        mapped_exc_class = super().map(exc)
        factory_args = {"entity_name": self.entity_name} if self.entity_name else {}
        return partial(mapped_exc_class, **factory_args)
