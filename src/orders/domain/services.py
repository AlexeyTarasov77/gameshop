from logging import Logger
from uuid import UUID
import asyncio
from core.pagination import PaginationParams
from core.services.base import BaseService
from core.services.exceptions import EntityNotFoundError, UnavailableProductError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import NotFoundError
from orders.schemas import (
    CreateOrderDTO,
    CreateOrderResDTO,
    ShowOrder,
    ShowOrderExtended,
    UpdateOrderDTO,
)
from payments.domain.interfaces import PaymentSystemFactoryI
from users.domain.interfaces import MailProviderI


class OrdersService(BaseService):
    entity_name = "Order"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        logger: Logger,
        mail_provider: MailProviderI,
        payment_system_factory: PaymentSystemFactoryI,
        order_details_link: str,
    ):
        super().__init__(uow, logger)
        self._mail_provider = mail_provider
        self._order_details_link = order_details_link
        self._payment_system_factory = payment_system_factory

    async def create_order(
        self,
        dto: CreateOrderDTO,
        user_id: int | None,
    ) -> CreateOrderResDTO:
        self._logger.info("Creating order for user: %s with data: %s", user_id, dto)
        try:
            async with self._uow as uow:
                cart_products = await uow.products_repo.list_by_ids(
                    [int(item.product_id) for item in dto.cart]
                )
                assert len(cart_products) == len(dto.cart)
                for product in cart_products:
                    if not product.in_stock:
                        self._logger.warning(
                            "Attempt to create order with unavailable product %s",
                            product.id,
                        )
                        raise UnavailableProductError(product.name)
                order = await uow.orders_repo.create_from_dto(dto, user_id)
                user_email: str | None = dto.user.email
                if user_id is not None:
                    user = await uow.users_repo.get_by_id(user_id, is_active=True)
                    user_email = user.email
                await uow.order_items_repo.create_many(dto.cart, order.id)
        except NotFoundError:
            # user not found
            self._logger.warning(
                "OrdersService.create_order: suspicious attempt to create order from unexistent/inactive user with valid auth token. user_id from token: %s",
                user_id,
            )
            raise EntityNotFoundError("User", id=user_id)
        assert user_email
        payment_system = self._payment_system_factory.choose_by_name(
            dto.selected_system_name
        )
        self._logger.info(
            "Creating payment bill for %s payment system", dto.selected_system_name
        )
        bill_id, payment_url = await payment_system.create_bill(
            order.id, order.total, user_email
        )
        self._logger.info("New bill created: %s", bill_id)
        email_body = (
            f"Ваш заказ был успешно оформлен и принят в обработку.\n"
            "Для просмотра деталей заказа и отслеживания его статуса - перейдите по ссылке ниже\n"
            f"\t{self._order_details_link % order.id}\t"
        )
        asyncio.create_task(
            self._mail_provider.send_mail_with_timeout(
                "Спасибо за заказ!",
                email_body,
                to=user_email,
            )
        )
        self._logger.info(
            "Succesfully created order for user: %s. Order id: %s", user_email, order.id
        )
        return CreateOrderResDTO(
            order=ShowOrder.from_model(order, total=order.total),
            payment_url=payment_url,
        )

    async def update_order(self, dto: UpdateOrderDTO, order_id: UUID) -> ShowOrder:
        self._logger.info("Updating order: %s. Data: %s", order_id, dto)
        try:
            async with self._uow as uow:
                order = await uow.orders_repo.update_by_id(dto, order_id)
        except NotFoundError:
            self._logger.warning("Order %s not found", order_id)
            raise EntityNotFoundError(self.entity_name, id=order_id)
        return ShowOrder.from_model(order, total=order.total)

    async def delete_order(self, order_id: UUID) -> None:
        self._logger.info("Deleting order: %s", order_id)
        try:
            async with self._uow as uow:
                await uow.orders_repo.delete_by_id(order_id)
        except NotFoundError:
            self._logger.warning("Order %s not found", order_id)
            raise EntityNotFoundError(self.entity_name, id=order_id)

    async def list_orders_for_user(
        self, pagination_params: PaginationParams, user_id: int
    ) -> tuple[list[ShowOrderExtended], int]:
        self._logger.info(
            "Listing orders for user: %s. Pagination params: %s",
            user_id,
            pagination_params,
        )
        async with self._uow as uow:
            orders, total_records = await uow.orders_repo.list_orders_for_user(
                pagination_params,
                user_id,
            )
        return [
            ShowOrderExtended.from_model(
                order, items=order.items, user=order.user, total=order.total
            )
            for order in orders
        ], total_records

    async def list_all_orders(
        self, pagination_params: PaginationParams
    ) -> tuple[list[ShowOrderExtended], int]:
        self._logger.info(
            "Listing all orders. Pagination params: %s", pagination_params
        )
        async with self._uow as uow:
            orders, total_records = await uow.orders_repo.list_all_orders(
                pagination_params
            )
        return [
            ShowOrderExtended.from_model(
                order, items=order.items, user=order.user, total=order.total
            )
            for order in orders
        ], total_records

    async def get_order(self, order_id: UUID) -> ShowOrderExtended:
        self._logger.info("Fetching order by id: %s", order_id)
        try:
            async with self._uow as uow:
                order = await uow.orders_repo.get_by_id(order_id)
        except NotFoundError:
            self._logger.warning("Order %s not found", order_id)
            raise EntityNotFoundError(self.entity_name, id=order_id)
        return ShowOrderExtended.from_model(
            order, items=order.items, user=order.user, total=order.total
        )
