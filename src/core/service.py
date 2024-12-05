import logging
from functools import partial

from db.main import (
    AlreadyExistsError,
    DatabaseError,
    NotFoundError,
    RelatedResourceNotFoundError,
)

from core.uow import AbstractUnitOfWork


class ServiceError(Exception):
    def _generate_msg(self) -> str:
        return "unexpected service error"

    def __init__(self, entity_name: str, *args, **kwargs) -> None:
        self._entity_name = entity_name
        self._params = kwargs
        self.msg = self._generate_msg()
        return super().__init__(*args)


class EntityNotFoundError(ServiceError):
    def _generate_msg(self) -> str:
        msg = "%s %s not found"
        params_string = ""
        if self._params:
            params_string = "with " + ", ".join(f"{key}={value}" for key, value in self._params.items())
        return msg % (self._entity_name, params_string)


class EntityAlreadyExistsError(ServiceError):
    def _generate_msg(self) -> str:
        msg = "%s %s already exists"
        params_string = ""
        if self._params:
            params_string += "with " + ", ".join(f"{key}={value}" for key, value in self._params.items())
        return msg % (self._entity_name, params_string)


class EntityRelatedResourceNotFoundError(ServiceError):
    def _generate_msg(self) -> str:
        msg = "%s's related resources doesn't exist%s"
        params_string = ""
        if self.kwargs:
            params_string += ": " + ", ".join(f"{key}={value}" for key, value in self._params.items())
        return msg % (self._entity_name, params_string)


class BaseService:
    entity_name = None
    EXCEPTION_MAPPING: dict[type[DatabaseError], type[ServiceError]] = {
        NotFoundError: EntityNotFoundError,
        AlreadyExistsError: EntityAlreadyExistsError,
        RelatedResourceNotFoundError: EntityRelatedResourceNotFoundError,
    }

    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self.uow = uow

    @classmethod
    def map_db_exception(cls, exc: DatabaseError) -> partial[ServiceError]:
        mapped_exc = cls.EXCEPTION_MAPPING.get(type(exc), ServiceError)
        if mapped_exc is ServiceError:
            logging.warning("Not mapped exc: %s", exc)
        factory_args = {"entity_name": cls.entity_name} if cls.entity_name else {}
        return partial(mapped_exc, **factory_args)
