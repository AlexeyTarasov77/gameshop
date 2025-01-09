from core.service import BaseService
from gateways.db.exceptions import DatabaseError
from orders.schemas import CreateOrderDTO, BaseShowOrder


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
