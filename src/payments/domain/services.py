import asyncio
from collections.abc import Callable
from decimal import Decimal
from logging import Logger
from uuid import UUID
from core.services.base import BaseService
from core.services.exceptions import ActionForbiddenError, ExternalGatewayError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import NotFoundError
from mailing.domain.services import MailingService
from orders.domain.interfaces import SteamAPIClientI
from orders.models import (
    BaseOrder,
    OrderCategory,
    OrderStatus,
)
from orders.schemas import UpdateOrderDTO
from payments.domain.interfaces import (
    AvailablePaymentSystems,
    EmailTemplatesI,
    PaymentSystemFactoryI,
    TelegramClientI,
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
        email_templates: EmailTemplatesI,
        order_details_link_builder: Callable[[UUID], str],
        steam_api: SteamAPIClientI,
        admin_tg_chat_id: int,
        tg_client: TelegramClientI,
    ) -> None:
        super().__init__(uow, logger)
        self._mailing_service = mailing_service
        self._payment_system_factory = payment_system_factory
        self._email_templates = email_templates
        self._order_details_link_builder = order_details_link_builder
        self._steam_api = steam_api
        self._tg_client = tg_client
        self._admin_tg_chat_id = admin_tg_chat_id

    async def _mark_order_as_paid(
        self, dto: ProcessOrderPaymentDTO, uow: AbstractUnitOfWork
    ):
        return await uow.orders_repo.update_payment_details(
            **dto.model_dump(), check_is_pending=True
        )

    async def _process_steam_gift_order(
        self, dto: ProcessOrderPaymentDTO, uow: AbstractUnitOfWork
    ) -> BaseOrder:
        order = await self._mark_order_as_paid(dto, uow)
        await self._steam_api.pay_gift_order(dto.order_id)
        return order

    async def _process_steam_top_up_order(
        self, dto: ProcessOrderPaymentDTO, uow: AbstractUnitOfWork
    ) -> BaseOrder:
        order = await self._mark_order_as_paid(dto, uow)
        await self._steam_api.top_up_complete(dto.order_id)
        return order

    async def _process_in_app_order(
        self, dto: ProcessOrderPaymentDTO, uow: AbstractUnitOfWork
    ) -> BaseOrder:
        order = await self._mark_order_as_paid(dto, uow)
        return order

    async def process_payment(
        self,
        status: str,
        order_id: UUID,
        order_total: Decimal,
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
        additional_msg = ""
        try:
            async with self._uow() as uow:
                try:
                    match payment_for:
                        case OrderCategory.IN_APP:
                            order = await self._process_in_app_order(
                                process_order_dto, uow
                            )
                            customer_tg = (
                                await uow.in_app_orders_repo.get_customer_tg_by_id(
                                    order.id
                                )
                            )
                            if customer_tg[0] != "@":
                                customer_tg = "@" + customer_tg
                            additional_msg = f"Телеграм заказчика: {customer_tg}"
                        case OrderCategory.STEAM_TOP_UP:
                            order = await self._process_steam_top_up_order(
                                process_order_dto, uow
                            )
                        case OrderCategory.STEAM_GIFT:
                            order = await self._process_steam_gift_order(
                                process_order_dto, uow
                            )
                except ExternalGatewayError:
                    await uow.orders_repo.update_by_id(
                        UpdateOrderDTO(status=OrderStatus.FAILED), order_id
                    )
                    raise

            admin_notification_msg = (
                f"Заказ #{order.id} успешно оплачен!\n"
                f"Сумма: {order_total} ₽\n"
                f"Email заказчика: {order.customer_email} 📧\n"
                f"Дата заказа: {order.order_date} 📆\n"
                f"Тип заказа: {str(order.category.value)}\n" + additional_msg
            )
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
            await self._tg_client.send_msg(
                self._admin_tg_chat_id, admin_notification_msg
            )
        except NotFoundError:
            self._logger.error(
                "Trying to pay for not active or not found order. Order id: %s",
                order_id,
            )
            raise ActionForbiddenError("Order not found")
