import re

from pydantic import BaseModel
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase


class SqlAlchemyBaseModel(DeclarativeBase):
    repr_cols_num: int = 3
    repr_cols: tuple = ()
    model_schema: BaseModel | None = None

    def __repr__(self):
        cols = []
        for i, col in enumerate(self.__table__.columns.keys()):
            if i < self.repr_cols_num or col in self.repr_cols:
                cols.append(f"{col}={getattr(self, col)!r}")
        return f"<{self.__class__.__name__}({', '.join(cols)})>"

    def to_read_model(self):
        readable_model = {col: getattr(self, col) for col in self.__table__.columns.keys()}
        if self.model_schema:
            readable_model = self.model_schema.model_validate(self).model_dump()
        return readable_model

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        snake_case_name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
        return snake_case_name
