from enum import IntEnum, StrEnum

from sqlalchemy.orm import Mapped


class AvailablePaymentSystems(StrEnum):
    PAYPALYCH = "paypalych"


class PaymentType(IntEnum):
    ORDER = 1
    STEAM_TOP_UP = 2


class PaymentMixin:
    bill_id: Mapped[str | None]
    paid_with: Mapped[AvailablePaymentSystems | None]
