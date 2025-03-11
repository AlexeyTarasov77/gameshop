from gateways.db.sqlalchemy_gateway import int_pk_type, created_at_type, updated_at_type

from sqlalchemy.orm import Mapped
from gateways.db.sqlalchemy_gateway import SqlAlchemyBaseModel


class News(SqlAlchemyBaseModel):
    id: Mapped[int_pk_type]
    title: Mapped[str]
    description: Mapped[str]
    photo_url: Mapped[str | None]
    created_at: Mapped[created_at_type]
    updated_at: Mapped[updated_at_type]
