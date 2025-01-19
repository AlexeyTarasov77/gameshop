from core.pagination import PaginationParams
from core.service import BaseService
from gateways.db.exceptions import DatabaseError
from orders.schemas import (
    CreateOrderDTO,
    BaseShowOrder,
    ShowOrderWithRelations,
    UpdateOrderDTO,
)


class ServiceValidationError(Exception): ...


class OrdersService(BaseService):
    async def create_order(
        self, dto: CreateOrderDTO, user_id: int | None
    ) -> BaseShowOrder:
        dto.user.user_id = user_id
        if not (dto.user.user_id or (dto.user.email and dto.user.name)):
            raise ServiceValidationError(
                "email and name are required for not authorized user"
            )
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

    async def list_orders_for_user(
        self, pagination_params: PaginationParams, user_id: int
    ) -> tuple[list[ShowOrderWithRelations], int]:
        try:
            async with self.uow as uow:
                orders = await uow.orders_repo.list_orders_for_user(
                    limit=pagination_params.page_size,
                    offset=pagination_params.calc_offset(),
                    user_id=user_id,
                )
                total_records = await uow.orders_repo.get_records_count()
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)() from e
        return [
            ShowOrderWithRelations.model_validate(order) for order in orders
        ], total_records

    async def list_all_orders(
        self, pagination_params: PaginationParams
    ) -> tuple[list[ShowOrderWithRelations], int]:
        try:
            async with self.uow as uow:
                orders = await uow.orders_repo.list_all_orders(
                    limit=pagination_params.page_size,
                    offset=pagination_params.calc_offset(),
                )
                total_records = await uow.orders_repo.get_records_count()
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)() from e
        return [
            ShowOrderWithRelations.model_validate(order) for order in orders
        ], total_records

    async def get_order(self, order_id: int) -> ShowOrderWithRelations:
        try:
            async with self.uow as uow:
                order = await uow.orders_repo.get_by_id(order_id)
        except DatabaseError as e:
            raise self.exception_mapper.map_with_entity(e)() from e
        return ShowOrderWithRelations.model_validate(order)
