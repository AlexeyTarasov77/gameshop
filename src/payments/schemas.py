from uuid import UUID

from core.api.schemas import BaseDTO
from payments.models import AvailablePaymentSystems


class ProcessOrderPaymentDTO(BaseDTO):
    paid_with: AvailablePaymentSystems
    order_id: UUID
    bill_id: str


class PaymentBillDTO(BaseDTO):
    bill_id: str
    payment_url: str
