from collections.abc import Sequence
from typing import Protocol
from uuid import UUID
from core.pagination import PaginationParams, PaginationResT
from orders.schemas import CreateOrderDTO, SteamTopUpCreateDTO, UpdateOrderDTO
from orders.models import Order, OrderItem, SteamTopUp
from payments.models import AvailablePaymentSystems
from products.schemas import ExchangeRatesMappingDTO


class OrdersRepositoryI(Protocol):
    async def create_from_dto(
        self, dto: CreateOrderDTO, user_id: int | None
    ) -> Order: ...
    async def update_by_id(self, dto: UpdateOrderDTO, order_id: UUID) -> Order: ...
    async def update_for_payment(
        self, bill_id: str, paid_with: AvailablePaymentSystems, order_id: UUID
    ) -> Order: ...
    async def delete_by_id(self, order_id: UUID) -> None: ...
    async def list_orders_for_user(
        self, pagination_params: PaginationParams, user_id: int
    ) -> PaginationResT[Order]: ...
    async def list_all_orders(
        self, pagination_params: PaginationParams
    ) -> PaginationResT[Order]: ...
    async def get_by_id(self, order_id: UUID) -> Order: ...


class OrderItemsRepositoryI(Protocol):
    async def save_many(self, entities: Sequence[OrderItem]) -> None: ...


class SteamAPIClientI(Protocol):
    async def create_top_up_request(self, dto: SteamTopUpCreateDTO) -> UUID: ...
    async def get_currency_rates(self) -> ExchangeRatesMappingDTO: ...


class SteamTopUpRepositoryI(Protocol):
    async def create_with_id(
        self,
        dto: SteamTopUpCreateDTO,
        order_id: UUID,
        percent_fee: int,
        user_id: int | None,
    ) -> SteamTopUp: ...


class TopUpFeeManagerI(Protocol):
    async def set_current_fee(self, percent_fee: int) -> None: ...
    async def get_current_fee(self) -> int | None: ...
