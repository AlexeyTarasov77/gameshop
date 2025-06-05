from core.logging import AbstractLogger
from core.uow import AbstractUnitOfWork


class BaseService:
    entity_name: str

    def __init__(self, uow: AbstractUnitOfWork, logger: AbstractLogger) -> None:
        self._uow = uow
        self._logger = logger
        assert self.entity_name
