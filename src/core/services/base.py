from core.uow import AbstractUnitOfWork
from core.exception_mappers import ServiceExceptionMapper


class BaseService:
    entity_name = None

    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow
        self._exception_mapper = ServiceExceptionMapper(self.entity_name)
