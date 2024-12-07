import re
from abc import ABC, abstractmethod
from collections.abc import Mapping

from gateways.db.exceptions import NotFoundError
from gateways.db.models import SqlAlchemyBaseModel
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class AbstractRepository[T](ABC):
    @abstractmethod
    async def create(self, **values) -> T: ...

    @abstractmethod
    async def list(self, **filter_by) -> list[T]: ...

    @classmethod
    def get_shortname(cls) -> str:
        """Computes repo short name. Example:
        ProductsRepository.get_shortname() -> products_repo
        """

        name = cls.__name__
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        snake_case_name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

        if not snake_case_name.endswith("_repository"):
            raise ValueError("Incorrect repo name")
        short_name = snake_case_name.replace("_repository", "_repo")

        return short_name


class SqlAlchemyRepository[T: type[SqlAlchemyBaseModel]](AbstractRepository[T]):
    model: T

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **values) -> T:
        instance = self.model(**values)
        self.session.add(instance)
        return instance

    async def list(self, *fields, **filter_by) -> list[T]:
        query = select(*fields or self.model).filter_by(**filter_by)
        results = await self.session.execute(query)
        return results.scalars().all()

    async def update(self, data: Mapping, **filter_by) -> T:
        query = update(self.model).filter_by(**filter_by).values(**data).returning(self.model)
        updated_object = await self.session.execute(query)
        if updated_object:
            return updated_object.scalars().first()

    async def delete(self, **filter_by) -> int:
        query = delete(self.model).filter_by(**filter_by)
        res = await self.session.execute(query)
        if res.rowcount < 1:
            raise NotFoundError()
