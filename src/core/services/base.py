from logging import Logger
from core.uow import AbstractUnitOfWork


class BaseService:
    entity_name: str

    def __init__(self, uow: AbstractUnitOfWork, logger: Logger) -> None:
        self._uow = uow
        self._logger = logger
