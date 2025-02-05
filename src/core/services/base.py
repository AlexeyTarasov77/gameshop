from contextlib import contextmanager
from core.uow import AbstractUnitOfWork
from core.exception_mappers import ServiceExceptionMapper
from gateways.db.exceptions import DatabaseError


class BaseService:
    entity_name: str

    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow
        assert self.entity_name
        self._exception_mapper = ServiceExceptionMapper(self.entity_name)

    @contextmanager
    def handle_exc(self, **params):
        try:
            yield
        except DatabaseError as e:
            raise self._exception_mapper.map_and_init(e, **params) from e
