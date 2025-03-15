from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from gateways.db.sqlalchemy_gateway import created_at_type, int_pk_type, updated_at_type
from gateways.db.sqlalchemy_gateway import SqlAlchemyBaseModel, TimestampMixin
from sqlalchemy.dialects.postgresql import BYTEA, CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship


if TYPE_CHECKING:
    from orders.models import Order


class User(SqlAlchemyBaseModel, TimestampMixin):
    __allow_unmapped__ = True
    is_admin: bool | None = None

    id: Mapped[int_pk_type]
    username: Mapped[str]
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    password_hash: Mapped[bytes] = mapped_column(BYTEA)
    photo_url: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=False)
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class TokenScopes(StrEnum):
    ACTIVATION = "activation"
    PASSWORD_RESET = "password-reset"


class Admin(SqlAlchemyBaseModel):
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )


class Token(SqlAlchemyBaseModel):
    scope: Mapped[TokenScopes]
    hash: Mapped[bytes] = mapped_column(BYTEA, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    expiry: Mapped[datetime]
