import asyncio
from collections.abc import Callable
from logging import Logger
from uuid import UUID
from core.services.base import BaseService
from core.services.exceptions import ActionForbiddenError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import NotFoundError
from mailing.domain.services import MailingService
from orders.domain.interfaces import SteamAPIClientI
from orders.models import InAppOrder, OrderCategory, SteamTopUpOrder
from payments.domain.interfaces import (
    AvailablePaymentSystems,
    PaymentEmailTemplatesI,
    PaymentSystemFactoryI,
)
from payments.schemas import ProcessOrderPaymentDTO


class PaymentsService(BaseService):
    entity_name = "Payment"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        logger: Logger,
        payment_system_factory: PaymentSystemFactoryI,
        mailing_service: MailingService,
        email_templates: PaymentEmailTemplatesI,
        order_details_link_builder: Callable[[UUID], str],
        steam_api: SteamAPIClientI,
    ) -> None:
        super().__init__(uow, logger)
        self._mailing_service = mailing_service
        self._payment_system_factory = payment_system_factory
        self._email_templates = email_templates
        self._order_details_link_builder = order_details_link_builder
        self._steam_api = steam_api

    async def _process_steam_top_up_order(
        self, dto: ProcessOrderPaymentDTO, uow: AbstractUnitOfWork
    ) -> SteamTopUpOrder:
        order = await uow.steam_top_up_repo.update_payment_details(
            **dto.model_dump(), check_is_pending=True
        )
        await self._steam_api.top_up_complete(dto.order_id)
        return order

    async def _process_in_app_order(
        self, dto: ProcessOrderPaymentDTO, uow: AbstractUnitOfWork
    ) -> InAppOrder:
        order = await uow.orders_repo.update_payment_details(
            **dto.model_dump(), check_is_pending=True
        )
        return order

    async def process_payment(
        self,
        status: str,
        order_id: UUID,
        bill_id: str,
        ps_name: AvailablePaymentSystems,
        payment_for: OrderCategory,
    ):
        payment_system = self._payment_system_factory.choose_by_name(ps_name)
        if not payment_system.is_success(status):
            self._logger.warning(
                "Payment for order %s failed with status: %s. bill_id: %s",
                order_id,
                status,
                bill_id,
            )
            return
        process_order_dto = ProcessOrderPaymentDTO(
            paid_with=ps_name, order_id=order_id, bill_id=bill_id
        )
        try:
            async with self._uow as uow:
                match payment_for:
                    case OrderCategory.IN_APP:
                        order = await self._process_in_app_order(process_order_dto, uow)
                    case OrderCategory.STEAM_TOP_UP:
                        order = await self._process_steam_top_up_order(
                            process_order_dto, uow
                        )

        except NotFoundError:
            self._logger.error(
                "Trying to pay for not active or not found order. Order id: %s",
                order_id,
            )
            raise ActionForbiddenError("Order not found")

        email_body = await self._email_templates.order_checkout(
            self._order_details_link_builder(order_id), order_id
        )
        asyncio.create_task(
            self._mailing_service.send_mail(
                "Спасибо за заказ!",
                email_body,
                to=order.client_email,
            )
        )
