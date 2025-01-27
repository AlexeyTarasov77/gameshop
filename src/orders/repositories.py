from collections.abc import Sequence
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from core.pagination import PaginationParams
from gateways.db.exceptions import NotFoundError
from gateways.db.repository import PaginationRepository, SqlAlchemyRepository
from orders.models import Order, OrderItem
from orders.schemas import (
    CreateOrderDTO,
    OrderItemCreateDTO,
    UpdateOrderDTO,
)
from products.models import Product


class OrdersRepository(PaginationRepository[Order]):
    model = Order

    def _get_select_stmt(self):
        return (
            select(self.model)
            .join(self.model.user)
            .options(selectinload(self.model.items))
        )

    async def create(self, dto: CreateOrderDTO, user_id: int | None) -> Order:
        return await super().create(
            **{"customer_" + k: v for k, v in dto.user},
            user_id=user_id,
        )

    async def update_by_id(self, dto: UpdateOrderDTO, order_id: UUID) -> Order:
        return await super().update(dto.model_dump(), id=order_id)

    async def delete_by_id(self, order_id: UUID) -> None:
        return await super().delete_or_raise_not_found(id=order_id)

    def _get_rels_load_options(self):
        return selectinload(self.model.items).options(
            joinedload(OrderItem.product).load_only(Product.id, Product.name)
        )

    async def _paginated_list(self, pagination_params: PaginationParams, **filter_by):
        stmt = (
            super()
            ._get_pagination_stmt(pagination_params)
            .options(self._get_rels_load_options())
            .filter_by(**filter_by)
        )

        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def list_orders_for_user(
        self, pagination_params: PaginationParams, user_id: int
    ) -> Sequence[Order]:
        return await self._paginated_list(pagination_params, user_id=user_id)

    async def list_all_orders(
        self, pagination_params: PaginationParams
    ) -> Sequence[Order]:
        return await self._paginated_list(pagination_params)

    async def get_by_id(self, order_id: UUID) -> Order:
        stmt = (
            select(self.model)
            .filter_by(id=order_id)
            .options(self._get_rels_load_options())
        )
        res = await self.session.execute(stmt)
        order = res.scalars().one_or_none()
        if not order:
            raise NotFoundError()
        return order


class OrderItemsRepository(SqlAlchemyRepository[OrderItem]):
    model = OrderItem

    async def create_many(
        self, dto_list: list[OrderItemCreateDTO], order_id: UUID
    ) -> list[OrderItem]:
        return [
            await super().create(
                **dto.model_dump(exclude={"product_id"}),
                order_id=order_id,
                product_id=dto.product_id,
            )
            for dto in dto_list
        ]
