from collections.abc import Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import (
    joinedload,
    selectin_polymorphic,
    selectinload,
    with_polymorphic,
)
from core.pagination import PaginationParams, PaginationResT
from core.schemas import OrderByOption
from gateways.db.exceptions import NotFoundError
from gateways.db import RedisClient
from gateways.db.sqlalchemy_gateway import PaginationRepository, SqlAlchemyRepository
from orders.models import (
    BaseOrder,
    InAppOrder,
    InAppOrderItem,
    OrderStatus,
    SteamGiftOrder,
    SteamTopUpOrder,
)
from orders.schemas import (
    CreateInAppOrderDTO,
    CreateSteamGiftOrderDTO,
    CreateSteamTopUpOrderDTO,
    ListOrdersParamsDTO,
    UpdateOrderDTO,
)
from payments.models import AvailablePaymentSystems
from products.models import Product


class OrdersRepoMixin[T: BaseOrder](SqlAlchemyRepository[T]):
    async def _save_order(self, order_obj: T) -> T:
        self._session.add(order_obj)
        await self._session.flush()
        self._session.expunge(order_obj)
        return order_obj


class OrdersRepository(PaginationRepository[BaseOrder]):
    model = BaseOrder

    async def update_payment_details(
        self,
        bill_id: str,
        paid_with: AvailablePaymentSystems,
        order_id: UUID,
        *,
        check_is_pending: bool,
    ) -> BaseOrder:
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

    async def update_by_id(self, dto: UpdateOrderDTO, order_id: UUID) -> BaseOrder:
        return await super().update(dto.model_dump(), id=order_id)

    async def list_orders(
        self,
        pagination_params: PaginationParams,
        dto: ListOrdersParamsDTO,
    ) -> PaginationResT[BaseOrder]:
        stmt = (
            super()
            ._get_pagination_stmt(pagination_params)
            .options(
                selectin_polymorphic(self.model, self.model.__subclasses__()),
                selectinload(InAppOrder.items).load_only(
                    InAppOrderItem.price, InAppOrderItem.quantity
                ),
            )
        )
        if dto.category is not None:
            stmt = stmt.filter_by(category=dto.category)
        if dto.user_id is not None:
            stmt = stmt.filter_by(user_id=dto.user_id)
        if dto.status is not None:
            stmt = stmt.filter_by(status=dto.status)
        if dto.date_ordering is not None:
            option = {OrderByOption.ASC: sa.asc, OrderByOption.DESC: sa.desc}[
                dto.date_ordering
            ]
            stmt = stmt.order_by(option(self.model.order_date))
        res = await self._session.execute(stmt)
        return super()._split_records_and_count(res.all())

    async def delete_by_id(self, order_id: UUID) -> None:
        await super().delete_or_raise_not_found(id=order_id)

    async def get_by_id(self, order_id: UUID) -> BaseOrder:
        stmt = sa.select(with_polymorphic(self.model, "*")).filter_by(id=order_id)
        res = await self._session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise NotFoundError("order not found")
        return obj


class InAppOrdersRepository(
    OrdersRepoMixin[InAppOrder], PaginationRepository[InAppOrder]
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

    async def delete_by_id(self, order_id: UUID) -> None:
        return await super().delete_or_raise_not_found(id=order_id)

    def _get_rels_load_options(self):
        return selectinload(self.model.items).options(
            joinedload(InAppOrderItem.product).load_only(Product.id, Product.name)
        )

    async def get_by_id(self, order_id: UUID) -> InAppOrder:
        stmt = (
            sa.select(self.model)
            .filter_by(id=order_id)
            .options(self._get_rels_load_options())
        )
        res = await self._session.execute(stmt)
        order = res.scalars().one_or_none()
        if not order:
            raise NotFoundError()
        return order

    async def get_customer_tg_by_id(self, order_id: UUID) -> str:
        customer_tg = await self._session.scalar(
            sa.select(self.model.customer_tg_username).filter_by(id=order_id)
        )
        if customer_tg is None:
            raise NotFoundError()
        return customer_tg


class SteamTopUpRepository(OrdersRepoMixin[SteamTopUpOrder]):
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
            **dto.model_dump(exclude={"rub_amount", "selected_ps"}),
        )
        return await super()._save_order(order_obj)

    async def get_by_id(self, order_id: UUID):
        return await super().get_one(id=order_id)


class SteamGiftsRepository(OrdersRepoMixin[SteamGiftOrder]):
    model = SteamGiftOrder

    async def create_with_id(
        self,
        dto: CreateSteamGiftOrderDTO,
        order_id: UUID,
        user_id: int | None,
        total: Decimal,
    ) -> SteamGiftOrder:
        order_obj = SteamGiftOrder(
            id=order_id,
            user_id=user_id,
            total=total,
            **dto.model_dump(exclude={"rub_amount", "selected_ps"}),
        )
        return await super()._save_order(order_obj)


class TopUpFeeManager:
    def __init__(self, db: RedisClient):
        self._db = db
        self._key = "steam_top_up_fee"

    async def set_current_fee(self, percent_fee: int) -> None:
        await self._db.set(self._key, percent_fee)

    async def get_current_fee(self) -> int | None:
        fee = await self._db.get(self._key)
        return None if fee is None else int(fee)
