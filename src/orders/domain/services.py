from logging import Logger
from uuid import UUID
from core.pagination import PaginationParams
from core.services.base import BaseService
from core.services.exceptions import (
    EntityNotFoundError,
    ClientError,
    UnavailableProductError,
)
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import NotFoundError
from orders.domain.interfaces import SteamAPIClientI, TopUpFeeManagerI
from orders.models import (
    InAppOrder,
    InAppOrderItem,
    OrderCategory,
    SteamTopUpOrder,
)
from orders.schemas import (
    CreateInAppOrderDTO,
    OrderPaymentDTO,
    InAppOrderDTO,
    InAppOrderExtendedDTO,
    CreateSteamTopUpOrderDTO,
    SteamTopUpOrderDTO,
    UpdateOrderDTO,
)
from payments.domain.interfaces import PaymentSystemFactoryI
from payments.models import AvailablePaymentSystems
from payments.schemas import PaymentBillDTO


class OrdersService(BaseService):
    entity_name = "Order"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        logger: Logger,
        payment_system_factory: PaymentSystemFactoryI,
        top_up_fee_manager: TopUpFeeManagerI,
        steam_api: SteamAPIClientI,
    ):
        super().__init__(uow, logger)
        self._payment_system_factory = payment_system_factory
        self._steam_api = steam_api
        self._top_up_fee_manager = top_up_fee_manager
        self._top_up_default_fee = 10  # %

    async def _create_payment_bill(
        self,
        ps_name: AvailablePaymentSystems,
        order_like_obj: InAppOrder | SteamTopUpOrder,
    ) -> PaymentBillDTO:
        payment_system = self._payment_system_factory.choose_by_name(ps_name)
        self._logger.info("Creating payment bill for %s payment system", ps_name)
        return await payment_system.create_bill(
            order_like_obj.id,
            order_like_obj.total,
            order_like_obj.client_email,
            OrderCategory.IN_APP
            if isinstance(order_like_obj, InAppOrder)
            else OrderCategory.STEAM_TOP_UP,
        )

    async def create_in_app_order(
        self,
        dto: CreateInAppOrderDTO,
        user_id: int | None,
    ) -> OrderPaymentDTO[InAppOrderDTO]:
        self._logger.info("Creating order for user: %s with data: %s", user_id, dto)
        async with self._uow as uow:
            cart_products = await uow.products_repo.list_by_ids(
                [int(item.product_id) for item in dto.cart], only_in_stock=True
            )
            if len(cart_products) != len(dto.cart):
                raise EntityNotFoundError(
                    "Some of the supplied products not found or aren't in stock anymore"
                )
            order_items: list[InAppOrderItem] = []
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
                        mapped_price_by_region = regional_price.calc_discounted_price(
                            product.discount
                        )
                if mapped_price_by_region is None:
                    raise UnavailableProductError(product.name)
                order_items.append(
                    InAppOrderItem(
                        region=region or None,
                        price=mapped_price_by_region,
                        product_id=product.id,
                        quantity=mapped_item.quantity,
                    )
                )
            order = await uow.orders_repo.create_from_dto(dto, user_id, order_items)
            payment_dto = await self._create_payment_bill(dto.selected_ps, order)
        self._logger.info(
            "Succesfully placed an order for user: %s. Order id: %s, bill id: %s",
            order.client_email,
            order.id,
            payment_dto.bill_id,
        )
        return OrderPaymentDTO(
            order=InAppOrderDTO.model_validate(order),
            payment_url=payment_dto.payment_url,
        )

    async def update_order(self, dto: UpdateOrderDTO, order_id: UUID) -> InAppOrderDTO:
        self._logger.info("Updating order: %s. Data: %s", order_id, dto)
        try:
            async with self._uow as uow:
                order = await uow.orders_repo.update_by_id(dto, order_id)
        except NotFoundError:
            self._logger.warning("Order %s not found", order_id)
            raise EntityNotFoundError(self.entity_name, id=order_id)
        return InAppOrderDTO.model_validate(order)

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
    ) -> tuple[list[InAppOrderExtendedDTO], int]:
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
            InAppOrderExtendedDTO.model_validate(order) for order in orders
        ], total_records

    # TODO: Return both in app and steam top up orders
    async def list_all_orders(
        self, pagination_params: PaginationParams
    ) -> tuple[list[InAppOrderExtendedDTO], int]:
        self._logger.info(
            "Listing all orders. Pagination params: %s", pagination_params
        )
        async with self._uow as uow:
            orders, total_records = await uow.orders_repo.list_all_orders(
                pagination_params
            )
        return [
            InAppOrderExtendedDTO.model_validate(order) for order in orders
        ], total_records

    async def get_order(self, order_id: UUID) -> InAppOrderExtendedDTO:
        self._logger.info("Fetching order by id: %s", order_id)
        try:
            async with self._uow as uow:
                order = await uow.orders_repo.get_by_id(order_id)
        except NotFoundError:
            self._logger.warning("Order %s not found", order_id)
            raise EntityNotFoundError(self.entity_name, id=order_id)
        return InAppOrderExtendedDTO.model_validate(order)

    async def steam_top_up(
        self, dto: CreateSteamTopUpOrderDTO, user_id: int | None
    ) -> OrderPaymentDTO[SteamTopUpOrderDTO]:
        try:
            top_up_id = await self._steam_api.create_top_up_request(dto)
        except ValueError as e:
            raise ClientError(str(e))
        percent_fee = await self._top_up_fee_manager.get_current_fee()
        if percent_fee is None:
            self._logger.warning(
                "Steam top up fee is unset. Using default: %s", self._top_up_default_fee
            )
            percent_fee = self._top_up_default_fee
        async with self._uow as uow:
            top_up = await uow.steam_top_up_repo.create_with_id(
                dto, top_up_id, percent_fee, user_id
            )
            payment_dto = await self._create_payment_bill(dto.selected_ps, top_up)
        self._logger.info(
            "Succesfully created steam top up order. Top-Up id: %s, bill id: %s, client_email: %s",
            top_up.id,
            payment_dto.bill_id,
            top_up.client_email,
        )
        return OrderPaymentDTO(
            order=SteamTopUpOrderDTO.model_validate(top_up),
            payment_url=payment_dto.payment_url,
        )

    async def set_steam_top_up_fee(self, percent_fee: int) -> None:
        await self._top_up_fee_manager.set_current_fee(percent_fee)

    async def get_steam_top_up_fee(self) -> int:
        return (
            await self._top_up_fee_manager.get_current_fee() or self._top_up_default_fee
        )
