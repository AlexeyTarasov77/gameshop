from logging import Logger
from uuid import UUID
from core.services.base import BaseService
from core.uow import AbstractUnitOfWork
from payments.domain.interfaces import AvailablePaymentSystems, PaymentSystemFactoryI


class PaymentsService(BaseService):
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
            await uow.orders_repo.update_for_payment(
                bill_id,
                payment_system_name,
                order_id,
            )
