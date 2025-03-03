import asyncio
from collections.abc import Callable
from logging import Logger
from uuid import UUID
from core.services.base import BaseService
from core.services.exceptions import ActionForbiddenError
from core.uow import AbstractUnitOfWork
from orders.models import OrderStatus
from payments.domain.interfaces import (
    AvailablePaymentSystems,
    PaymentEmailTemplatesI,
    PaymentSystemFactoryI,
)
from users.domain.interfaces import MailProviderI


class PaymentsService(BaseService):
    entity_name = "Payment"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        logger: Logger,
        payment_system_factory: PaymentSystemFactoryI,
        mail_provider: MailProviderI,
        email_templates: PaymentEmailTemplatesI,
        order_details_link_builder: Callable[[UUID], str],
    ) -> None:
        super().__init__(uow, logger)
        self._mail_provider = mail_provider
        self._payment_system_factory = payment_system_factory
        self._email_templates = email_templates
        self._order_details_link_builder = order_details_link_builder

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
            order = await uow.orders_repo.get_by_id(order_id)
            if order.status != OrderStatus.PENDING:
                self._logger.error(
                    "Trying to pay for not active order with status: %s", order.status
                )
                raise ActionForbiddenError("Order has been already processed!")
            order = await uow.orders_repo.update_for_payment(
                bill_id,
                payment_system_name,
                order_id,
            )

        asyncio.create_task(
            self._mail_provider.send_mail_with_timeout(
                "Спасибо за заказ!",
                self._email_templates.order_checkout(
                    self._order_details_link_builder(order_id), order_id
                ),
                to=order.client_email,
            )
        )
