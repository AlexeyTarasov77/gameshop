from collections.abc import Sequence
from typing import Any
from uuid import UUID
from redis.asyncio import Redis
from sqlalchemy import desc, func, select
from sqlalchemy.orm import joinedload, selectin_polymorphic, selectinload
from core.pagination import PaginationParams, PaginationResT
from gateways.db.exceptions import NotFoundError
from gateways.db.sqlalchemy_gateway import PaginationRepository, SqlAlchemyRepository
from orders.models import (
    BaseOrder,
    InAppOrder,
    InAppOrderItem,
    OrderCategory,
    OrderStatus,
    SteamTopUpOrder,
)
from orders.schemas import (
    CreateInAppOrderDTO,
    CreateSteamTopUpOrderDTO,
    UpdateOrderDTO,
)
from payments.models import AvailablePaymentSystems
from products.models import Product


class OrdersRepositoryMixin[T: BaseOrder](SqlAlchemyRepository):
    async def update_payment_details(
        self,
        bill_id: str,
        paid_with: AvailablePaymentSystems,
        order_id: UUID,
        *,
        check_is_pending: bool,
    ) -> T:
        filters: dict[str, Any] = {"id": order_id}
        if check_is_pending:
            filters["status"] = OrderStatus.PENDING
        return await super().update(
            {
                "bill_id": bill_id,
                "paid_with": paid_with,
                "status": OrderStatus.COMPLETED,
            },
            **filters,
        )


class OrdersRepository(PaginationRepository[BaseOrder]):
    model = BaseOrder

    async def update_by_id(self, dto: UpdateOrderDTO, order_id: UUID) -> BaseOrder:
        return await super().update(dto.model_dump(), id=order_id)

    def _get_category_filter(self, category: OrderCategory | None) -> dict:
        filter_by = {}
        if category is not None:
            filter_by["category"] = category
        return filter_by

    async def list_orders(
        self, pagination_params: PaginationParams, category: OrderCategory | None = None
    ) -> PaginationResT[BaseOrder]:
        stmt = (
            super()
            ._get_pagination_stmt(pagination_params)
            .options(selectin_polymorphic(BaseOrder, [InAppOrder, SteamTopUpOrder]))
            .filter_by(**self._get_category_filter(category))
        )
        res = await self._session.execute(stmt)
        records = res.all()
        # res = await self._session.execute(
        #     select(InAppOrderItem).where(
        #         InAppOrderItem.order_id.in_([rec[0].id for rec in records])
        #     )
        # )
        return super()._split_records_and_count(records)
        # return await super().paginated_list(
        #     pagination_params, **self._get_category_filter(category)
        # )

    async def list_orders_for_user(
        self,
        pagination_params: PaginationParams,
        user_id: int,
        category: OrderCategory | None = None,
    ) -> PaginationResT[BaseOrder]:
        return await super().paginated_list(
            pagination_params,
            user_id=user_id,
            **self._get_category_filter(category),
        )

    async def delete_by_id(self, order_id: UUID) -> None:
        await super().delete_or_raise_not_found(id=order_id)

    async def get_by_id(self, order_id: UUID) -> BaseOrder:
        print("SUBCLASSES", BaseOrder.__subclasses__())
        stmt = (
            select(self.model)
            .filter_by(id=order_id)
            .options(selectin_polymorphic(BaseOrder, BaseOrder.__subclasses__()))
        )
        res = await self._session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise NotFoundError("order not found")
        return obj


class InAppOrdersRepository(
    OrdersRepositoryMixin[InAppOrder], PaginationRepository[InAppOrder]
):
    model = InAppOrder

    async def create_with_items(
        self,
        dto: CreateInAppOrderDTO,
        user_id: int | None,
        items: Sequence[InAppOrderItem],
    ) -> InAppOrder:
        data = {"customer_" + k: v for k, v in dto.user}
        order_obj = InAppOrder(**data, user_id=user_id, items=items)
        self._session.add(order_obj)
        await self._session.flush()
        self._session.expunge(order_obj)
        return order_obj

    async def update_by_id(self, dto: UpdateOrderDTO, order_id: UUID) -> InAppOrder:
        return await super().update(dto.model_dump(), id=order_id)

    # async def update_payment_details(
    #     self,
    #     bill_id: str,
    #     paid_with: AvailablePaymentSystems,
    #     order_id: UUID,
    #     *,
    #     check_is_pending: bool,
    # ) -> InAppOrder:
    #     filters: dict[str, Any] = {"id": order_id}
    #     if check_is_pending:
    #         filters["status"] = OrderStatus.PENDING
    #     return await super().update(
    #         {
    #             "bill_id": bill_id,
    #             "paid_with": paid_with,
    #             "status": OrderStatus.COMPLETED,
    #         },
    #         **filters,
    #     )
    #
    async def delete_by_id(self, order_id: UUID) -> None:
        return await super().delete_or_raise_not_found(id=order_id)

    def _get_rels_load_options(self):
        return selectinload(self.model.items).options(
            joinedload(InAppOrderItem.product).load_only(Product.id, Product.name)
        )

    async def _paginated_list(
        self, pagination_params: PaginationParams, **filter_by
    ) -> PaginationResT[model]:
        stmt = (
            super()
            ._get_pagination_stmt(pagination_params)
            .options(self._get_rels_load_options())
            .filter_by(**filter_by)
            .order_by(desc(InAppOrder.order_date))
        )

        res = await self._session.execute(stmt)
        return super()._split_records_and_count(res.all())

    async def list_orders_for_user(
        self, pagination_params: PaginationParams, user_id: int
    ) -> PaginationResT[model]:
        return await self._paginated_list(pagination_params, user_id=user_id)

    async def list_all_orders(
        self, pagination_params: PaginationParams
    ) -> PaginationResT[model]:
        return await self._paginated_list(pagination_params)

    async def get_by_id(self, order_id: UUID) -> InAppOrder:
        stmt = (
            select(self.model)
            .filter_by(id=order_id)
            .options(self._get_rels_load_options())
        )
        res = await self._session.execute(stmt)
        order = res.scalars().one_or_none()
        if not order:
            raise NotFoundError()
        return order


class SteamTopUpRepository(OrdersRepositoryMixin[SteamTopUpOrder]):
    model = SteamTopUpOrder

    async def create_with_id(
        self,
        dto: CreateSteamTopUpOrderDTO,
        order_id: UUID,
        percent_fee: int,
        user_id: int | None,
    ) -> SteamTopUpOrder:
        order_obj = SteamTopUpOrder(
            id=order_id,
            percent_fee=percent_fee,
            amount=dto.rub_amount,
            user_id=user_id,
            **dto.model_dump(include={"steam_login", "customer_email"}),
        )
        self._session.add(order_obj)
        await self._session.flush()
        self._session.expunge(order_obj)
        return order_obj

    async def get_by_id(self, order_id: UUID):
        return await super().get_one(id=order_id)

    # async def update_payment_details(
    #     self,
    #     bill_id: str,
    #     paid_with: AvailablePaymentSystems,
    #     order_id: UUID,
    #     *,
    #     check_is_pending: bool,
    # ):
    #     filters: dict[str, Any] = {"id": order_id}
    #     if check_is_pending:
    #         filters["status"] = OrderStatus.PENDING
    #     return await super().update(
    #         {
    #             "bill_id": bill_id,
    #             "paid_with": paid_with,
    #             "status": OrderStatus.COMPLETED,
    #         },
    #         **filters,
    #     )


class TopUpFeeManager:
    def __init__(self, db: Redis):
        self._db = db
        self._key = "steam_top_up_fee"

    async def set_current_fee(self, percent_fee: int) -> None:
        await self._db.set(self._key, percent_fee)

    async def get_current_fee(self) -> int | None:
        fee = await self._db.get(self._key)
        return None if fee is None else int(fee)
