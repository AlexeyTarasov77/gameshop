from decimal import Decimal
from typing import Protocol
from uuid import UUID

from mailing.domain.interfaces import MailingTemplate
from orders.models import OrderCategory
from payments.models import AvailablePaymentSystems
from payments.schemas import PaymentBillDTO


class PaymentSystemI(Protocol):
    async def create_bill(
        self,
        order_id: UUID,
        order_total: Decimal | int,
        customer_email: str,
        payment_for: OrderCategory,
    ) -> PaymentBillDTO: ...

    def is_success(self, status: str) -> bool: ...

    def sig_verify(
        self, sig_value: str, order_id: UUID, order_total: Decimal
    ) -> bool: ...


class EmailTemplatesI(Protocol):
    async def order_checkout(
        self, order_details_link: str, order_id: UUID
    ) -> MailingTemplate | str: ...


class PaymentSystemFactoryI(Protocol):
    def choose_by_name(self, name: AvailablePaymentSystems) -> PaymentSystemI: ...


class TelegramClientI(Protocol):
    async def send_msg(self, chat_id: int, text: str): ...
