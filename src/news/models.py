from gateways.db.column_types import int_pk_type, created_at_type, updated_at_type

from sqlalchemy.orm import Mapped
from gateways.db.models import SqlAlchemyBaseModel
from news.schemas import ShowNews


class News(SqlAlchemyBaseModel):
    model_schema = ShowNews

    id: Mapped[int_pk_type]
    title: Mapped[str]
    description: Mapped[str]
    photo_url: Mapped[str | None]
    created_at: Mapped[created_at_type]
    updated_at: Mapped[updated_at_type]
