from collections.abc import Sequence
from typing import Protocol
from uuid import UUID
from core.pagination import PaginationParams, PaginationResT
from orders.schemas import CreateInAppOrderDTO, CreateSteamTopUpOrderDTO, UpdateOrderDTO
from orders.models import (
    BaseOrder,
    InAppOrder,
    InAppOrderItem,
    OrderCategory,
    SteamTopUpOrder,
)
from payments.models import AvailablePaymentSystems
from gateways.currency_converter import ExchangeRatesMappingDTO


class OrdersRepositoryI(Protocol):
    async def update_by_id(self, dto: UpdateOrderDTO, order_id: UUID) -> BaseOrder: ...
    async def delete_by_id(self, order_id: UUID) -> None: ...
    async def get_by_id(self, order_id: UUID) -> BaseOrder: ...
    async def list_orders_for_user(
        self,
        pagination_params: PaginationParams,
        user_id: int,
        category: OrderCategory | None = None,
    ) -> PaginationResT[BaseOrder]: ...
    async def list_orders(
        self, pagination_params: PaginationParams, category: OrderCategory | None = None
    ) -> PaginationResT[BaseOrder]: ...


class InAppOrdersRepositoryI(Protocol):
    async def create_with_items(
        self,
        dto: CreateInAppOrderDTO,
        user_id: int | None,
        items: Sequence[InAppOrderItem],
    ) -> InAppOrder: ...
    async def update_payment_details(
        self,
        bill_id: str,
        paid_with: AvailablePaymentSystems,
        order_id: UUID,
        *,
        check_is_pending: bool,
    ) -> InAppOrder: ...


class SteamAPIClientI(Protocol):
    async def create_top_up_request(self, dto: CreateSteamTopUpOrderDTO) -> UUID: ...
    async def get_currency_rates(self) -> ExchangeRatesMappingDTO: ...
    async def top_up_complete(self, top_up_id: UUID): ...


class SteamTopUpRepositoryI(Protocol):
    async def create_with_id(
        self,
        dto: CreateSteamTopUpOrderDTO,
        order_id: UUID,
        percent_fee: int,
        user_id: int | None,
    ) -> SteamTopUpOrder: ...
    async def update_payment_details(
        self,
        bill_id: str,
        paid_with: AvailablePaymentSystems,
        order_id: UUID,
        *,
        check_is_pending: bool,
    ) -> SteamTopUpOrder: ...


class TopUpFeeManagerI(Protocol):
    async def set_current_fee(self, percent_fee: int) -> None: ...
    async def get_current_fee(self) -> int | None: ...
