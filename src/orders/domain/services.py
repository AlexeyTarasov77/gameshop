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
    ShowOrder,
    ShowOrderExtended,
    UpdateOrderDTO,
)
from users.domain.interfaces import MailProviderI


class OrdersService(BaseService):
    entity_name = "Order"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        logger: Logger,
        mail_provider: MailProviderI,
        order_details_link: str,
    ):
        super().__init__(uow, logger)
        self._mail_provider = mail_provider
        self._order_details_link = order_details_link

    async def create_order(self, dto: CreateOrderDTO, user_id: int | None) -> ShowOrder:
        try:
            async with self._uow as uow:
                cart_products = await uow.products_repo.list_by_ids(
                    [int(item.product_id) for item in dto.cart]
                )
                for product in cart_products:
                    if not product.in_stock:
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
        email_body = (
            f"Ваш заказ был успешно оформлен и принят в обработку.\n"
            "Для просмотра деталей заказа и отслеживания его статуса - перейдите по ссылке ниже\n"
            f"\t{self._order_details_link % order.id}\t"
        )
        assert user_email
        asyncio.create_task(
            self._mail_provider.send_mail_with_timeout(
                "Спасибо за заказ!",
                email_body,
                to=user_email,
            )
        )
        return ShowOrder.from_model(order, total=order.total)

    async def update_order(self, dto: UpdateOrderDTO, order_id: UUID) -> ShowOrder:
        try:
            async with self._uow as uow:
                order = await uow.orders_repo.update_by_id(dto, order_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=order_id)
        return ShowOrder.from_model(order, total=order.total)

    async def delete_order(self, order_id: UUID) -> None:
        try:
            async with self._uow as uow:
                await uow.orders_repo.delete_by_id(order_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=order_id)

    async def list_orders_for_user(
        self, pagination_params: PaginationParams, user_id: int
    ) -> tuple[list[ShowOrderExtended], int]:
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
        try:
            async with self._uow as uow:
                order = await uow.orders_repo.get_by_id(order_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=order_id)
        return ShowOrderExtended.from_model(
            order, items=order.items, user=order.user, total=order.total
        )
