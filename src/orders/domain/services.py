from decimal import Decimal
from logging import Logger
from uuid import UUID

from pydantic_extra_types.country import CountryAlpha2
from core.pagination import PaginationParams, PaginationResT
from core.schemas import EMPTY_REGION
from core.services.base import BaseService
from core.services.exceptions import (
    EntityNotFoundError,
    ClientError,
    UnavailableProductError,
)
from core.uow import AbstractUnitOfWork
from core.utils import normalize_s
from gateways.db.exceptions import NotFoundError
from orders.domain.interfaces import SteamAPIClientI, TopUpFeeManagerI
from orders.models import (
    BaseOrder,
    InAppOrderItem,
    OrderCategory,
)
from orders import schemas
from payments.domain.interfaces import PaymentSystemFactoryI
from payments.models import AvailablePaymentSystems
from payments.schemas import PaymentBillDTO
from products.models import ProductDeliveryMethod, ProductPlatform


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

    def _order_to_dto(self, order: BaseOrder):
        mapping: dict[OrderCategory, type[schemas.ShowBaseOrderDTO]] = {
            OrderCategory.IN_APP: schemas.InAppOrderExtendedDTO,
            OrderCategory.STEAM_TOP_UP: schemas.SteamTopUpOrderExtendedDTO,
            OrderCategory.STEAM_GIFT: schemas.SteamGiftOrderDTO,
        }
        return mapping[order.category].model_validate(order)

    async def _create_payment_bill(
        self,
        ps_name: AvailablePaymentSystems,
        order: BaseOrder,
        category: OrderCategory,
    ) -> PaymentBillDTO:
        payment_system = self._payment_system_factory.choose_by_name(ps_name)
        self._logger.info("Creating payment bill for %s payment system", ps_name)
        return await payment_system.create_bill(
            order.id, round(order.total), order.client_email, category
        )

    async def create_in_app_order(
        self,
        dto: schemas.CreateInAppOrderDTO,
        user_id: int | None,
    ) -> schemas.OrderPaymentDTO[schemas.InAppOrderDTO]:
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
                [cart_item] = [
                    item for item in dto.cart if item.product_id == product.id
                ]
                if (
                    product.platform == ProductPlatform.XBOX
                    and "region" not in cart_item.model_fields_set
                ):
                    cart_item.region = CountryAlpha2("us")
                # find price for provided region
                region = normalize_s(cart_item.region)
                mapped_price = None
                for regional_price in product.prices:
                    if normalize_s(regional_price.region_code) == region:
                        mapped_price = regional_price.calc_discounted_price(
                            product.discount
                        )
                if mapped_price is None:
                    raise UnavailableProductError(product.name, region)
                order_items.append(
                    InAppOrderItem(
                        region=region,
                        price=mapped_price,
                        product_id=product.id,
                        quantity=cart_item.quantity,
                    )
                )
            order = await uow.in_app_orders_repo.create_with_items(
                dto, user_id, order_items
            )
            if not dto.user.email:
                assert user_id
                user = await uow.users_repo.get_by_id(user_id)
                order.set_user(user)
            payment_dto = await self._create_payment_bill(
                dto.selected_ps, order, OrderCategory.IN_APP
            )
        self._logger.info(
            "Succesfully placed an order for user: %s. Order id: %s, bill id: %s",
            order.client_email,
            order.id,
            payment_dto.bill_id,
        )
        return schemas.OrderPaymentDTO(
            order=schemas.InAppOrderDTO.model_validate(order),
            payment_url=payment_dto.payment_url,
        )

    async def update_order(
        self, dto: schemas.UpdateOrderDTO, order_id: UUID
    ) -> schemas.ShowBaseOrderDTO:
        self._logger.info("Updating order: %s. Data: %s", order_id, dto)
        try:
            async with self._uow as uow:
                order = await uow.orders_repo.update_by_id(dto, order_id)
        except NotFoundError:
            self._logger.warning("Order %s not found", order_id)
            raise EntityNotFoundError(self.entity_name, id=order_id)
        return schemas.ShowBaseOrderDTO.model_validate(order)

    async def delete_order(self, order_id: UUID) -> None:
        self._logger.info("Deleting order: %s", order_id)
        try:
            async with self._uow as uow:
                await uow.orders_repo.delete_by_id(order_id)
        except NotFoundError:
            self._logger.warning("Order %s not found", order_id)
            raise EntityNotFoundError(self.entity_name, id=order_id)

    async def list_orders_for_user(
        self,
        pagination_params: PaginationParams,
        user_id: int,
        category: OrderCategory | None,
    ) -> PaginationResT[schemas.ShowBaseOrderDTO]:
        self._logger.info(
            "Listing orders for user: %s. Pagination params: %s",
            user_id,
            pagination_params,
        )
        async with self._uow as uow:
            orders, total_records = await uow.orders_repo.list_orders_for_user(
                pagination_params, user_id, category
            )
        return [
            schemas.ShowBaseOrderDTO.model_validate(order) for order in orders
        ], total_records

    async def list_all_orders(
        self, pagination_params: PaginationParams, category: OrderCategory | None
    ) -> PaginationResT[schemas.ShowBaseOrderDTO]:
        self._logger.info(
            "Listing all orders. Pagination params: %s", pagination_params
        )
        async with self._uow as uow:
            orders, total_records = await uow.orders_repo.list_orders(
                pagination_params, category
            )
        return [
            schemas.ShowBaseOrderDTO.model_validate(order) for order in orders
        ], total_records

    async def get_order(self, order_id: UUID) -> schemas.ShowBaseOrderDTO:
        self._logger.info("Fetching order by id: %s", order_id)
        try:
            async with self._uow as uow:
                order = await uow.orders_repo.get_by_id(order_id)
        except NotFoundError:
            self._logger.warning("Order %s not found", order_id)
            raise EntityNotFoundError(self.entity_name, id=order_id)
        return self._order_to_dto(order)

    async def create_steam_top_up_order(
        self, dto: schemas.CreateSteamTopUpOrderDTO, user_id: int | None
    ) -> schemas.OrderPaymentDTO[schemas.SteamTopUpOrderDTO]:
        try:
            top_up_id = await self._steam_api.create_top_up_order(dto)
        except ValueError as e:
            raise ClientError(str(e))
        percent_fee = await self._top_up_fee_manager.get_current_fee()
        if percent_fee is None:
            self._logger.warning(
                "Steam top up fee is unset. Using default: %s", self._top_up_default_fee
            )
            percent_fee = self._top_up_default_fee
        async with self._uow as uow:
            order = await uow.steam_top_up_repo.create_with_id(
                dto, top_up_id, percent_fee, user_id
            )
            payment_dto = await self._create_payment_bill(
                dto.selected_ps, order, OrderCategory.STEAM_TOP_UP
            )
        self._logger.info(
            "Succesfully created steam top up order. Top-Up id: %s, bill id: %s, client_email: %s",
            order.id,
            payment_dto.bill_id,
            order.client_email,
        )
        return schemas.OrderPaymentDTO(
            order=schemas.SteamTopUpOrderDTO.model_validate(order),
            payment_url=payment_dto.payment_url,
        )

    async def set_steam_top_up_fee(self, percent_fee: int) -> None:
        await self._top_up_fee_manager.set_current_fee(percent_fee)

    async def get_steam_top_up_fee(self) -> int:
        return (
            await self._top_up_fee_manager.get_current_fee() or self._top_up_default_fee
        )

    async def create_steam_gift_order(
        self, dto: schemas.CreateSteamGiftOrderDTO, user_id: int | None
    ) -> schemas.OrderPaymentDTO[schemas.SteamGiftOrderDTO]:
        product_id = int(dto.product_id)
        try:
            async with self._uow as uow:
                product = await uow.products_repo.get_by_id(product_id)
                if product.delivery_method != ProductDeliveryMethod.GIFT:
                    raise ClientError(
                        f"You can't buy that product as gift. Available only: {product.delivery_method.value.label}"
                    )
                assert product.sub_id
                order_total: Decimal | None = None
                for price in product.prices:
                    if normalize_s(price.region_code) == EMPTY_REGION:
                        order_total = price.total_price
                if order_total is None:
                    self._logger.error(
                        "Unable to find price for product. Product id: %d",
                        product.id,
                    )
                    raise UnavailableProductError(
                        "That product is currently unavailable. Try to use another delivery method or try again later"
                    )
                try:
                    gift_id = await self._steam_api.create_gift_order(
                        dto, product.sub_id
                    )
                except ValueError as e:
                    raise ClientError(str(e))
                order = await uow.steam_gifts_repo.create_with_id(
                    dto, gift_id, user_id, order_total
                )
                order.product = product
                payment_dto = await self._create_payment_bill(
                    dto.selected_ps, order, OrderCategory.STEAM_GIFT
                )
        except NotFoundError:
            raise EntityNotFoundError("Product", id=dto.product_id)
        self._logger.info(
            "Succesfully created steam gift order. Order id: %s, bill id: %s, client_email: %s",
            order.id,
            payment_dto.bill_id,
            order.client_email,
        )
        return schemas.OrderPaymentDTO(
            order=schemas.SteamGiftOrderDTO.model_validate(order),
            payment_url=payment_dto.payment_url,
        )
