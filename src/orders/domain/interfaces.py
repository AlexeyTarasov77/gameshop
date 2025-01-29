from collections.abc import Sequence
from typing import Protocol
from uuid import UUID
from core.pagination import PaginationParams, PaginationResT
from orders.schemas import CreateOrderDTO, OrderItemCreateDTO, UpdateOrderDTO
from orders.models import Order, OrderItem


class OrdersRepositoryI(Protocol):
    async def create(self, dto: CreateOrderDTO, user_id: int | None) -> Order: ...
    async def update_by_id(self, dto: UpdateOrderDTO, order_id: UUID) -> Order: ...
    async def delete_by_id(self, order_id: UUID) -> None: ...
    async def list_orders_for_user(
        self, pagination_params: PaginationParams, user_id: int
    ) -> PaginationResT[Order]: ...
    async def list_all_orders(
        self, pagination_params: PaginationParams
    ) -> PaginationResT[Order]: ...
    async def get_by_id(self, order_id: UUID) -> Order: ...


class OrderItemsRepositoryI(Protocol):
    async def create_many(
        self, dto_list: list[OrderItemCreateDTO], order_id: UUID
    ) -> list[OrderItem]: ...
