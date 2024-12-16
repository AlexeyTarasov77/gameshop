import re
from abc import ABC, abstractmethod
from collections.abc import Mapping

from gateways.db.exceptions import DatabaseError, NotFoundError
from gateways.db.models import SqlAlchemyBaseModel
from sqlalchemy import delete, insert, select, update
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
    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **values) -> T:
        if not values:
            raise DatabaseError("No data to insert")
        stmt = insert(self.model).values(**values).returning(self.model)
        res = await self.session.execute(stmt)
        return res.scalars().one()

    async def list(self, *columns, **filter_by) -> list[T]:
        stmt = select(self.model)
        if columns:
            stmt = select(*[getattr(self.model.columns, col) for col in columns])
        stmt = stmt.filter_by(**filter_by)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get_one(self, *columns, **filter_by) -> T:
        res = await self.list(*columns, **filter_by)
        if not res:
            raise NotFoundError()
        return res[0]

    async def update(self, data: Mapping, **filter_by) -> T:
        if not data:
            raise DatabaseError("No data to update. Provided data is empty")
        stmt = update(self.model).filter_by(**filter_by).values(**data).returning(self.model)
        res = await self.session.execute(stmt)
        obj = res.scalars().one_or_none()
        if not obj:
            raise NotFoundError()
        return obj

    async def delete(self, **filter_by) -> int:
        stmt = delete(self.model).filter_by(**filter_by)
        res = await self.session.execute(stmt)
        if res.rowcount < 1:
            raise NotFoundError()
