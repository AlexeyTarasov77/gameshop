from core.service import BaseService
from gateways.db.exceptions import DatabaseError
from orders.schemas import CreateOrderDTO, BaseShowOrder, UpdateOrderDTO


class ServiceValidationError(Exception): ...


class OrdersService(BaseService):
    async def create_order(
        self, dto: CreateOrderDTO, user_id: int | None
    ) -> BaseShowOrder:
        dto.user.user_id = user_id
        if not any([dto.user.user_id, dto.user.email]):
            raise ServiceValidationError("email is required for not authorized user")
        async with self.uow as uow:
            try:
                order = await uow.orders_repo.create(dto)
                await uow.order_items_repo.create_many(dto.cart, order.id)
            except DatabaseError as e:
                raise self.exception_mapper.map_with_entity(e)(
                    **dto.model_dump()
                ) from e
        return BaseShowOrder.model_validate(order)

    async def update_order(self, dto: UpdateOrderDTO, order_id: int) -> BaseShowOrder:
        try:
            async with self.uow as uow:
                order = await uow.orders_repo.update_by_id(dto, order_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(
                id=order_id,
            ) from e
        return BaseShowOrder.model_validate(order)

    async def delete_order(self, order_id: int) -> None:
        try:
            async with self.uow as uow:
                await uow.orders_repo.delete_by_id(order_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)(
                id=order_id,
            ) from e
