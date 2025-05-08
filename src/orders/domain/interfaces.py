from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol
from uuid import UUID
from core.pagination import PaginationParams, PaginationResT
from orders.schemas import (
    CreateInAppOrderDTO,
    CreateSteamGiftOrderDTO,
    CreateSteamTopUpOrderDTO,
    ListOrdersParamsDTO,
    UpdateOrderDTO,
)
from orders.models import (
    BaseOrder,
    InAppOrder,
    InAppOrderItem,
    SteamGiftOrder,
    SteamTopUpOrder,
)
from payments.models import AvailablePaymentSystems
from gateways.currency_converter import ExchangeRatesMappingDTO


class AllOrdersRepositoryI(Protocol):
    async def update_by_id(self, dto: UpdateOrderDTO, order_id: UUID) -> BaseOrder: ...
    async def delete_by_id(self, order_id: UUID) -> None: ...
    async def get_by_id(self, order_id: UUID) -> BaseOrder: ...
    async def list_orders(
        self,
        pagination_params: PaginationParams,
        dto: ListOrdersParamsDTO,
    ) -> PaginationResT[BaseOrder]: ...
    async def update_payment_details(
        self,
        bill_id: str,
        paid_with: AvailablePaymentSystems,
        order_id: UUID,
        *,
        check_is_pending: bool,
    ) -> BaseOrder: ...


class InAppOrdersRepositoryI(Protocol):
    async def create_with_items(
        self,
        dto: CreateInAppOrderDTO,
        user_id: int | None,
        items: Sequence[InAppOrderItem],
    ) -> InAppOrder: ...

    async def get_customer_tg_by_id(self, order_id: UUID) -> str: ...


class SteamAPIClientI(Protocol):
    async def create_top_up_order(self, dto: CreateSteamTopUpOrderDTO) -> UUID: ...
    async def create_gift_order(
        self, dto: CreateSteamGiftOrderDTO, sub_id: int
    ) -> UUID: ...
    async def get_currency_rates(self) -> ExchangeRatesMappingDTO: ...
    async def top_up_complete(self, order_id: UUID): ...
    async def pay_gift_order(self, order_id: UUID): ...


class SteamTopUpRepositoryI(Protocol):
    async def create_with_id(
        self,
        dto: CreateSteamTopUpOrderDTO,
        order_id: UUID,
        percent_fee: int,
        user_id: int | None,
    ) -> SteamTopUpOrder: ...


class SteamGiftsRepositoryI(Protocol):
    async def create_with_id(
        self,
        dto: CreateSteamGiftOrderDTO,
        order_id: UUID,
        user_id: int | None,
        total: Decimal,
    ) -> SteamGiftOrder: ...


class TopUpFeeManagerI(Protocol):
    async def set_current_fee(self, percent_fee: int) -> None: ...
    async def get_current_fee(self) -> int | None: ...
