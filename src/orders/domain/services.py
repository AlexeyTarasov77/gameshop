from uuid import UUID
import asyncio
from core.pagination import PaginationParams
from core.services.base import BaseService
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import DatabaseError
from orders.schemas import (
    CreateOrderDTO,
    ShowOrder,
    ShowOrderExtended,
    UpdateOrderDTO,
)
from users.domain.interfaces import MailProviderI


class ServiceValidationError(Exception): ...


class OrdersService(BaseService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        mail_provider: MailProviderI,
        order_details_link: str,
    ):
        super().__init__(uow)
        self._mail_provider = mail_provider
        self._order_details_link = order_details_link

    async def create_order(self, dto: CreateOrderDTO, user_id: int | None) -> ShowOrder:
        if not (user_id or (dto.user.email and dto.user.name)):
            raise ServiceValidationError(
                "email and name are required for not authorized user"
            )
        try:
            async with self._uow as uow:
                cart_products = await uow.products_repo.list_by_ids(
                    [int(item.product_id) for item in dto.cart]
                )
                for product in cart_products:
                    if not product.in_stock:
                        raise ServiceValidationError(
                            f"Can't create order! Product {product.name} is not available"
                        )
                order = await uow.orders_repo.create(dto, user_id)
                user = None
                if user_id:
                    user = await uow.users_repo.get_by_id(user_id)
                await uow.order_items_repo.create_many(dto.cart, order.id)
        except DatabaseError as e:
            raise self._exception_mapper.map_with_entity(e)(**dto.model_dump()) from e
        email_body = (
            f"Ваш заказ был успешно оформлен и принят в обработку.\n"
            "Для просмотра деталей заказа и отслеживания его статуса - перейдите по ссылке ниже\n"
            f"\t{self._order_details_link % order.id}\t"
        )
        email_to = dto.user.email
        if not email_to:
            assert user is not None
            email_to = user.email
        asyncio.create_task(
            self._mail_provider.send_mail_with_timeout(
                "Спасибо за заказ!",
                email_body,
                to=email_to,
            )
        )
        return ShowOrder.from_model(order, total=order.total)

    async def update_order(self, dto: UpdateOrderDTO, order_id: UUID) -> ShowOrder:
        try:
            async with self._uow as uow:
                order = await uow.orders_repo.update_by_id(dto, order_id)
        except DatabaseError as e:
            raise self._exception_mapper.map(e)(
                id=order_id,
            ) from e
        return ShowOrder.from_model(order, total=order.total)

    async def delete_order(self, order_id: UUID) -> None:
        try:
            async with self._uow as uow:
                await uow.orders_repo.delete_by_id(order_id)
        except DatabaseError as e:
            raise self._exception_mapper.map(e)(
                id=order_id,
            ) from e

    async def list_orders_for_user(
        self, pagination_params: PaginationParams, user_id: int
    ) -> tuple[list[ShowOrderExtended], int]:
        try:
            async with self._uow as uow:
                orders, total_records = await uow.orders_repo.list_orders_for_user(
                    pagination_params,
                    user_id,
                )
        except DatabaseError as e:
            raise self._exception_mapper.map(e)() from e
        return [
            ShowOrderExtended.from_model(
                order, items=order.items, user=order.user, total=order.total
            )
            for order in orders
        ], total_records

    async def list_all_orders(
        self, pagination_params: PaginationParams
    ) -> tuple[list[ShowOrderExtended], int]:
        try:
            async with self._uow as uow:
                orders, total_records = await uow.orders_repo.list_all_orders(
                    pagination_params
                )
        except DatabaseError as e:
            raise self._exception_mapper.map(e)() from e
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
        except DatabaseError as e:
            raise self._exception_mapper.map(e)() from e
        return ShowOrderExtended.from_model(
            order, items=order.items, user=order.user, total=order.total
        )
