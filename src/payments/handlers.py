from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Form, HTTPException, status
import typing as t

from fastapi.responses import RedirectResponse

from core.ioc import Inject
from payments.domain.interfaces import AvailablePaymentSystems, PaymentSystemFactoryI
from payments.domain.services import PaymentsService


router = APIRouter(prefix="/payments", tags=["payments"])

PaymentsServiceDep = t.Annotated[PaymentsService, Inject(PaymentsService)]


class PayPalychSigVerifier:
    def __init__(
        self,
        InvId: t.Annotated[UUID, Form()],
        OutSum: t.Annotated[Decimal, Form()],
        SignatureValue: t.Annotated[str, Form()],
        payment_system_factory: t.Annotated[
            PaymentSystemFactoryI, Inject(PaymentSystemFactoryI)
        ],
    ):
        payment_system = payment_system_factory.choose_by_name(
            AvailablePaymentSystems.PAYPALYCH
        )
        self.order_id = InvId
        self.order_total = OutSum
        is_valid_sig = payment_system.sig_verify(
            SignatureValue, self.order_id, self.order_total
        )
        if not is_valid_sig:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Invalid signature in request body"
            )


@router.post("/paypalych")
async def paypalych_webhook(
    payments_service: PaymentsServiceDep,
    Status: t.Annotated[str, Form()],
    TrsId: t.Annotated[str, Form()],
    payload: t.Annotated[PayPalychSigVerifier, Depends()],
) -> dict[str, bool]:
    await payments_service.process_payment(
        Status,
        payload.order_id,
        TrsId,
        AvailablePaymentSystems.PAYPALYCH,
    )
    return {"success": True}


@router.post("/paypalych/success", dependencies=[Depends(PayPalychSigVerifier)])
async def payment_success(
    frontend_domain: t.Annotated[str, Inject("FRONTEND_DOMAIN")],
):
    return RedirectResponse(
        f"{frontend_domain}/cart/success", status.HTTP_303_SEE_OTHER
    )


@router.post("/paypalych/failed", dependencies=[Depends(PayPalychSigVerifier)])
async def payment_failed(
    frontend_domain: t.Annotated[str, Inject("FRONTEND_DOMAIN")],
):
    return RedirectResponse(f"{frontend_domain}/cart/failed", status.HTTP_303_SEE_OTHER)
