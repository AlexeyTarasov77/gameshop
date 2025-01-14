from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from gateways.db.repository import PaginationRepository, SqlAlchemyRepository
import asyncio
from orders.models import Order, OrderItem
from orders.schemas import (
    CreateOrderDTO,
    OrderItemCreateDTO,
    UpdateOrderDTO,
)


class OrdersRepository(PaginationRepository[Order]):
    model = Order

    def _get_select_stmt(self):
        return (
            select(self.model)
            .join(self.model.user)
            .options(selectinload(self.model.items))
        )

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

    async def list_orders_for_user(
        self, limit: int, offset: int, user_id: int
    ) -> Sequence[Order]:
        return await super().paginated_list(limit, offset, user_id=user_id)

    async def list_all_orders(self, limit: int, offset: int) -> Sequence[Order]:
        return await super().paginated_list(limit, offset)

    async def get_by_id(self, order_id: int) -> Order:
        return await super().get_one(id=order_id)


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
