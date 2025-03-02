from logging import Logger
from uuid import UUID
from core.services.base import BaseService
from core.services.exceptions import ActionForbiddenError
from core.uow import AbstractUnitOfWork
from orders.models import OrderStatus
from payments.domain.interfaces import AvailablePaymentSystems, PaymentSystemFactoryI


class PaymentsService(BaseService):
    entity_name = "Payment"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        logger: Logger,
        payment_system_factory: PaymentSystemFactoryI,
    ) -> None:
        super().__init__(uow, logger)
        self._payment_system_factory = payment_system_factory

    async def process_payment(
        self,
        status: str,
        order_id: UUID,
        bill_id: str,
        payment_system_name: AvailablePaymentSystems,
    ):
        payment_system = self._payment_system_factory.choose_by_name(
            payment_system_name
        )
        if not payment_system.is_success(status):
            self._logger.warning(
                "Payment for order %s failed with status: %s. bill_id: %s",
                order_id,
                status,
                bill_id,
            )
            return
        async with self._uow as uow:
            # TODO: check that order status is PENDING
            curr_status = await uow.orders_repo.get_status(order_id)
            if curr_status != OrderStatus.PENDING:
                self._logger.error(
                    "Trying to pay for not active order with status: %s", curr_status
                )
                raise ActionForbiddenError("Order has been already processed!")
            await uow.orders_repo.update_for_payment(
                bill_id,
                payment_system_name,
                order_id,
            )
