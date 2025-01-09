from typing import Protocol
from orders.schemas import CreateOrderDTO, OrderItemCreateDTO
from orders.models import Order, OrderItem


class OrdersRepositoryI(Protocol):
    async def create(self, dto: CreateOrderDTO) -> Order: ...


class OrderItemsRepositoryI(Protocol):
    async def create_many(
        self, dtos: list[OrderItemCreateDTO], order_id: int
    ) -> list[OrderItem]: ...
