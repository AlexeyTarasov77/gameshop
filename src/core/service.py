from functools import partial

from db.exceptions import (
    AlreadyExistsError,
    DatabaseError,
    NotFoundError,
    RelatedResourceNotFoundError,
)

from core.utils import AbstractExceptionMapper
from core.uow import AbstractUnitOfWork


class ServiceError(Exception):
    def _generate_msg(self) -> str:
        return "unexpected service error"

    def __init__(self, entity_name: str = "Unknown", *args, **kwargs) -> None:
        self._entity_name = entity_name
        self._params = kwargs
        self.msg = self._generate_msg()
        return super().__init__(*args)


class EntityNotFoundError(ServiceError):
    def _generate_msg(self) -> str:
        msg = "%s %s not found"
        params_string = ""
        if self._params:
            params_string = "with " + ", ".join(
                f"{key}={value}" for key, value in self._params.items()
            )
        return msg % (self._entity_name, params_string)


class EntityAlreadyExistsError(ServiceError):
    def _generate_msg(self) -> str:
        msg = "%s %s already exists"
        params_string = ""
        if self._params:
            params_string += "with " + ", ".join(
                f"{key}={value}" for key, value in self._params.items()
            )
        return msg % (self._entity_name, params_string)


class EntityRelatedResourceNotFoundError(ServiceError):
    def _generate_msg(self) -> str:
        msg = "%s's related resources doesn't exist%s"
        params_string = ""
        if self.kwargs:
            params_string += ": " + ", ".join(
                f"{key}={value}" for key, value in self._params.items()
            )
        return msg % (self._entity_name, params_string)


class ServiceExceptionMapper(AbstractExceptionMapper[DatabaseError, ServiceError]):
    def __init__(self, entity_name: str | None = None) -> None:
        self.entity_name = entity_name

    EXCEPTION_MAPPING = {
        NotFoundError: EntityNotFoundError,
        AlreadyExistsError: EntityAlreadyExistsError,
        RelatedResourceNotFoundError: EntityRelatedResourceNotFoundError,
    }

    @classmethod
    def get_default_exc(cls) -> type[ServiceError]:
        return ServiceError

    def map_with_entity(self, exc: DatabaseError) -> partial[ServiceError]:
        mapped_exc_class = super().map(exc)
        factory_args = {"entity_name": self.entity_name} if self.entity_name else {}
        return partial(mapped_exc_class, **factory_args)


class BaseService:
    entity_name = None

    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self.uow = uow
        self.exception_mapper = ServiceExceptionMapper(self.entity_name)
