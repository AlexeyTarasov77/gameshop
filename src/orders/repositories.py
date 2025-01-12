from gateways.db.repository import SqlAlchemyRepository
import asyncio
from orders.models import Order, OrderItem
from orders.schemas import CreateOrderDTO, OrderItemCreateDTO, UpdateOrderDTO


class OrdersRepository(SqlAlchemyRepository[Order]):
    model = Order

    async def create(self, dto: CreateOrderDTO) -> Order:
        return await super().create(
            customer_email=dto.user.email,
            customer_name=dto.user.name,
            customer_phone=dto.user.phone,
            customer_tg=dto.user.tg_username,
            user_id=dto.user.user_id,
        )

    async def update_by_id(self, dto: UpdateOrderDTO, order_id: int):
        return await super().update(dto.model_dump(), id=order_id)

    async def delete_by_id(self, order_id: int):
        return await super().delete(id=order_id)


class OrderItemsRepository(SqlAlchemyRepository[OrderItem]):
    model = OrderItem

    async def create_many(
        self, dtos: list[OrderItemCreateDTO], order_id: int
    ) -> list[OrderItem]:
        coros = [
            super().create(
                **dto.model_dump(exclude={"product_id"}),
                order_id=order_id,
                product_id=dto.product_id,
            )
            for dto in dtos
        ]
        return await asyncio.gather(*coros)
