import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Sequence

from core.pagination import PaginationParams
from gateways.db.exceptions import DatabaseError, NotFoundError
from gateways.db.models import SqlAlchemyBaseModel
from sqlalchemy import CursorResult, delete, insert, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession


class AbstractRepository[T](ABC):
    @abstractmethod
    async def create(self, **values) -> T: ...

    @abstractmethod
    async def list(self, **filter_by) -> Sequence[T]: ...

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


class SqlAlchemyRepository[T: SqlAlchemyBaseModel](AbstractRepository[T]):
    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **values) -> T:
        if not values:
            raise DatabaseError("No data to insert")
        stmt = insert(self.model).values(**values).returning(self.model)
        res = await self.session.execute(stmt)
        return res.scalars().one()

    async def list(self, **filter_by) -> Sequence[T]:
        stmt = select(self.model).filter_by(**filter_by)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get_one(self, **filter_by) -> T:
        stmt = select(self.model).filter_by(**filter_by).limit(1)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise NotFoundError()
        return obj

    async def update(self, data: Mapping, **filter_by) -> T:
        if not data:
            raise DatabaseError("No data to update. Provided data is empty")
        stmt = (
            update(self.model)
            .filter_by(**filter_by)
            .values(**data)
            .returning(self.model)
        )
        res = await self.session.execute(stmt)
        obj = res.scalars().one_or_none()
        if not obj:
            raise NotFoundError()
        return obj

    async def delete(self, **filter_by) -> CursorResult:
        stmt = delete(self.model).filter_by(**filter_by)
        res = await self.session.execute(stmt)
        return res

    async def delete_or_raise_not_found(self, **filter_by) -> None:
        res = await self.delete(**filter_by)
        if res.rowcount < 1:
            raise NotFoundError()


class PaginationRepository[T: SqlAlchemyBaseModel](SqlAlchemyRepository[T]):
    def _get_pagination_stmt(self, pagination_params: PaginationParams):
        return (
            select(self.model)
            .offset(pagination_params.calc_offset())
            .limit(pagination_params.page_size)
        )

    async def paginated_list(
        self, pagination_params: PaginationParams, **filter_by
    ) -> Sequence[T]:
        stmt = self._get_pagination_stmt(pagination_params).filter_by(**filter_by)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get_records_count(self) -> int:
        stmt = text(f'SELECT COUNT(id) FROM "{self.model.__tablename__}"')
        res = await self.session.execute(stmt)
        count = res.scalar()
        if count is None:
            raise DatabaseError()
        return int(count)
