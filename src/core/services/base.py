from core.uow import AbstractUnitOfWork


class BaseService:
    entity_name: str

    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow
        assert self.entity_name
