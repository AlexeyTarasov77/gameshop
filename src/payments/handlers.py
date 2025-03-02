from uuid import UUID
from fastapi import APIRouter, Form
import typing as t

from core.ioc import Inject
from payments.domain.interfaces import AvailablePaymentSystems
from payments.domain.services import PaymentsService


router = APIRouter(prefix="/payments", tags=["payments"])

PaymentsServiceDep = t.Annotated[PaymentsService, Inject(PaymentsService)]


@router.post("/paypalych", status_code=204)
async def paypalych_webhook(
    payments_service: PaymentsServiceDep,
    Status: t.Annotated[str, Form()],
    InvId: t.Annotated[UUID, Form()],
    TrsId: t.Annotated[str, Form()],
    SignatureValue: t.Annotated[str, Form()],
):
    await payments_service.process_payment(
        Status,
        InvId,
        TrsId,
        AvailablePaymentSystems.PAYPALYCH,
    )
