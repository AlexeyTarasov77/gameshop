from gateways.db.column_types import created_at_type, int_pk_type, updated_at_type
from gateways.db.models import SqlAlchemyBaseModel
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from users.schemas import ShowUser


class User(SqlAlchemyBaseModel):
    model_schema = ShowUser
    id: Mapped[int_pk_type]
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    password_hash: Mapped[str]
    photo_url: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[created_at_type]
    updated_at: Mapped[updated_at_type]
