from uuid import UUID
from fastapi import APIRouter
import typing as t

from core.ioc import Inject
from payments.domain.interfaces import AvailablePaymentSystems
from payments.domain.services import PaymentsService


router = APIRouter(prefix="/payments", tags=["payments"])

PaymentsServiceDep = t.Annotated[PaymentsService, Inject(PaymentsService)]


@router.post("/paypalych", status_code=204)
async def paypalych_webhook(payments_service: PaymentsServiceDep, data: dict):
    await payments_service.process_payment(
        data["Status"],
        UUID(data["InvId"]),
        data["TrsId"],
        AvailablePaymentSystems.PAYPALYCH,
    )
