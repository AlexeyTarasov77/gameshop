from gateways.db.column_types import created_at_type, int_pk_type, updated_at_type
from gateways.db.models import SqlAlchemyBaseModel
from sqlalchemy.dialects.postgresql import BYTEA, CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from users.schemas import ShowUser


class User(SqlAlchemyBaseModel):
    model_schema = ShowUser
    id: Mapped[int_pk_type]
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    password_hash: Mapped[bytes] = mapped_column(BYTEA)
    photo_url: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=False)
    orders: Mapped[list["Order"]] = relationship(back_populates="user")  # noqa
    created_at: Mapped[created_at_type]
    updated_at: Mapped[updated_at_type]
