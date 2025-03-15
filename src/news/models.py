from gateways.db.sqlalchemy_gateway import int_pk_type

from sqlalchemy.orm import Mapped
from gateways.db.sqlalchemy_gateway import SqlAlchemyBaseModel
from gateways.db.sqlalchemy_gateway.models import TimestampMixin


class News(SqlAlchemyBaseModel, TimestampMixin):
    id: Mapped[int_pk_type]
    title: Mapped[str]
    description: Mapped[str]
    photo_url: Mapped[str | None]
