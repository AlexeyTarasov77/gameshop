from decimal import Decimal
from uuid import UUID
from httpx import AsyncClient

from payments.domain.interfaces import CreatedBill


class PaymentFailedError(Exception):
    def __init__(self, context: dict):
        msg = "Payment failed. Context: " + " ".join(
            [f"{key}={value}" for key, value in context.items()]
        )
        super().__init__(msg)


class PaypalychPaymentSystem:
    def __init__(self, auth_token: str, shop_id: str):
        self._auth_token = auth_token
        self._shop_id = shop_id
        self._client = AsyncClient()
        self._base_url = "https://pal24.pro/api/v1"

    async def create_bill(
        self, order_id: UUID, order_total: Decimal, customer_email: str
    ) -> CreatedBill:
        data = {
            "shop_id": self._shop_id,
            "order_id": order_id,
            "amount": order_total,
            "payer_email": customer_email,
        }
        resp = await self._client.post(
            self._base_url + "/bill/create",
            json=data,
            headers={"Authorization": f"Bearer {self._auth_token}"},
        )
        resp_data = resp.json()
        if not resp_data["success"]:
            raise PaymentFailedError(resp_data)
        return CreatedBill(resp_data["bill_id"], resp_data["link_page_url"])
