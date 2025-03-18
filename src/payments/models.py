from enum import StrEnum

from sqlalchemy.orm import Mapped


class AvailablePaymentSystems(StrEnum):
    PAYPALYCH = "paypalych"


class PaymentMixin:
    bill_id: Mapped[str | None]
    paid_with: Mapped[AvailablePaymentSystems | None]
