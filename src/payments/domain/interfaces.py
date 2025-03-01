from decimal import Decimal
from enum import StrEnum
from typing import NamedTuple, Protocol
from uuid import UUID


class AvailablePaymentSystems(StrEnum):
    PAYPALYCH = "paypalych"


class CreatedBill(NamedTuple):
    bill_id: str
    payment_url: str


class PaymentSystemI(Protocol):
    async def create_bill(
        self, order_id: UUID, order_total: Decimal, customer_email: str
    ) -> CreatedBill: ...


class PaymentSystemFactoryI(Protocol):
    def choose_by_name(self, name: AvailablePaymentSystems) -> PaymentSystemI: ...
