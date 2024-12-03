from core.uow import AbstractUnitOfWork


class BaseService:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self.uow = uow
