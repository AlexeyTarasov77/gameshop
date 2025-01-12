from typing import Protocol
from orders.schemas import CreateOrderDTO, OrderItemCreateDTO, UpdateOrderDTO
from orders.models import Order, OrderItem


class OrdersRepositoryI(Protocol):
    async def create(self, dto: CreateOrderDTO) -> Order: ...
    async def update_by_id(self, dto: UpdateOrderDTO, order_id: int) -> Order: ...
    async def delete_by_id(self, order_id: int) -> None: ...


class OrderItemsRepositoryI(Protocol):
    async def create_many(
        self, dtos: list[OrderItemCreateDTO], order_id: int
    ) -> list[OrderItem]: ...
