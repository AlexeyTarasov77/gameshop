from decimal import Decimal
from hashlib import md5
from uuid import UUID
from httpx import AsyncClient

from config import Config
from orders.models import OrderCategory
from payments.domain.interfaces import (
    PaymentSystemI,
)
from payments.models import AvailablePaymentSystems
from payments.schemas import PaymentBillDTO


class PaymentFailedError(Exception):
    def __init__(self, context: dict):
        msg = "Payment failed. Context: " + " ".join(
            [f"{key}={value}" for key, value in context.items()]
        )
        super().__init__(msg)


class PaypalychPaymentSystem:
    def __init__(self, api_token: str, shop_id: str, client: AsyncClient):
        self._api_token = api_token
        self._shop_id = shop_id
        self._client = client
        self._base_url = "https://pal24.pro/api/v1"

    async def create_bill(
        self,
        order_id: UUID,
        order_total: Decimal,
        customer_email: str,
        payment_for: OrderCategory,
    ) -> PaymentBillDTO:
        data = {
            "shop_id": self._shop_id,
            "order_id": str(order_id),
            "amount": str(order_total),
            "payer_email": customer_email,
            "custom": payment_for,
        }
        resp = await self._client.post(
            self._base_url + "/bill/create",
            json=data,
            headers={"Authorization": f"Bearer {self._api_token}"},
        )
        resp_data = resp.json()
        if not resp_data["success"]:
            raise PaymentFailedError(resp_data)
        return PaymentBillDTO(
            bill_id=resp_data["bill_id"], payment_url=resp_data["link_page_url"]
        )

    def is_success(self, status: str) -> bool:
        return status == "SUCCESS"

    def sig_verify(self, sig_value: str, order_id: UUID, order_total: Decimal) -> bool:
        new_sig = (
            md5(f"{order_total}:{order_id}:{self._api_token}".encode())
            .hexdigest()
            .upper()
        )
        return sig_value == new_sig


class PaymentSystemFactoryImpl:
    def __init__(self, cfg: Config, client: AsyncClient):
        self._systems_mapping = {
            AvailablePaymentSystems.PAYPALYCH: PaypalychPaymentSystem(
                cfg.payments.paypalych.api_token, cfg.payments.paypalych.shop_id, client
            )
        }

    def choose_by_name(self, name: AvailablePaymentSystems) -> PaymentSystemI:
        return self._systems_mapping[name]
