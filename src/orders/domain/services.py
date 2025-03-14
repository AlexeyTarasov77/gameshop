from logging import Logger
from uuid import UUID
from core.pagination import PaginationParams
from core.services.base import BaseService
from core.services.exceptions import EntityNotFoundError, UnavailableProductError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import NotFoundError
from orders.models import OrderItem
from orders.schemas import (
    CreateOrderDTO,
    CreateOrderResDTO,
    ShowOrder,
    ShowOrderExtended,
    UpdateOrderDTO,
)
from payments.domain.interfaces import PaymentSystemFactoryI


class OrdersService(BaseService):
    entity_name = "Order"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        logger: Logger,
        payment_system_factory: PaymentSystemFactoryI,
    ):
        super().__init__(uow, logger)
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
                    [int(item.product_id) for item in dto.cart], only_in_stock=True
                )
                if len(cart_products) != len(dto.cart):
                    raise EntityNotFoundError(
                        "Some of the supplied products not found or aren't in stock anymore"
                    )
                order = await uow.orders_repo.create_from_dto(dto, user_id)
                order_items: list[OrderItem] = []
                for product in cart_products:
                    [mapped_item] = [
                        item for item in dto.cart if item.product_id == product.id
                    ]
                    # find price for provided region
                    region = (
                        mapped_item.region.lower().strip() if mapped_item.region else ""
                    )
                    mapped_price_by_region = None
                    for regional_price in product.prices:
                        if regional_price.region_code.lower().strip() == region:
                            mapped_price_by_region = (
                                regional_price.calc_discounted_price(product.discount)
                            )
                    if mapped_price_by_region is None:
                        raise UnavailableProductError(product.name)
                    order_items.append(
                        OrderItem(
                            order_id=order.id,
                            region=region or None,
                            price=mapped_price_by_region,
                            product_id=product.id,
                            quantity=mapped_item.quantity,
                        )
                    )
                if not dto.user.email and user_id is not None:
                    user = await uow.users_repo.get_by_id(user_id, is_active=True)
                    order.user = user
                order.items = order_items
                await uow.order_items_repo.save_many(order_items)

                # creating payment bill
                payment_system = self._payment_system_factory.choose_by_name(
                    dto.selected_ps
                )
                self._logger.info(
                    "Creating payment bill for %s payment system", dto.selected_ps
                )
                bill_id, payment_url = await payment_system.create_bill(
                    order.id, order.total, order.client_email
                )
        except NotFoundError:
            # user not found
            self._logger.warning(
                "OrdersService.create_order: suspicious attempt to create order from unexistent/inactive user with valid auth token. user_id from token: %s",
                user_id,
            )
            raise EntityNotFoundError("User", id=user_id)
        self._logger.info(
            "Succesfully placed an order for user: %s. Order id: %s, bill id: %s",
            order.client_email,
            order.id,
            bill_id,
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
