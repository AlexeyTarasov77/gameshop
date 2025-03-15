from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from core.pagination import PaginatedResponse
from core.dependencies import PaginationDep
from core.ioc import Inject
import typing as t

from core.schemas import require_dto_not_empty
from orders.domain.services import OrdersService
from orders.schemas import (
    CreateOrderDTO,
    CreateOrderResDTO,
    SteamTopUpCreateDTO,
    SteamTopUpCreateResDTO,
    UpdateOrderDTO,
    ShowOrderExtended,
)
from users.dependencies import get_optional_user_id, get_user_id_or_raise, require_admin

router = APIRouter(prefix="/orders", tags=["orders"])

OrdersServiceDep = t.Annotated[OrdersService, Inject(OrdersService)]


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    dto: CreateOrderDTO,
    user_id: t.Annotated[int | None, Depends(get_optional_user_id)],
    orders_service: OrdersServiceDep,
) -> CreateOrderResDTO:
    if not (user_id or (dto.user.email and dto.user.name)):
        raise HTTPException(400, "email and name are required for not authorized user")
    return await orders_service.create_order(dto, user_id)


@router.patch("/update/{order_id}", dependencies=[Depends(require_admin)])
async def update_order(
    dto: UpdateOrderDTO, order_id: UUID, orders_service: OrdersServiceDep
):
    require_dto_not_empty(dto)
    return await orders_service.update_order(dto, order_id)


@router.delete(
    "/delete/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_order(order_id: UUID, orders_service: OrdersServiceDep):
    await orders_service.delete_order(order_id)


@router.get("/list", dependencies=[Depends(require_admin)])
async def list_all_orders(
    pagination_params: PaginationDep,
    orders_service: OrdersServiceDep,
) -> PaginatedResponse[ShowOrderExtended]:
    orders, total_records = await orders_service.list_all_orders(pagination_params)
    return PaginatedResponse.new_response(orders, total_records, pagination_params)


@router.get("/list-for-user")
async def list_orders_for_user(
    pagination_params: PaginationDep,
    orders_service: OrdersServiceDep,
    user_id: int = Depends(get_user_id_or_raise),
) -> PaginatedResponse[ShowOrderExtended]:
    orders, total_records = await orders_service.list_orders_for_user(
        pagination_params, user_id
    )
    return PaginatedResponse.new_response(orders, total_records, pagination_params)


@router.get("/detail/{order_id}")
async def get_order(
    order_id: UUID, orders_service: OrdersServiceDep
) -> ShowOrderExtended:
    return await orders_service.get_order(order_id)


@router.post("/steam/top-up")
async def steam_top_up(
    dto: SteamTopUpCreateDTO,
    orders_service: OrdersServiceDep,
    user_id: int | None = Depends(get_optional_user_id),
) -> SteamTopUpCreateResDTO:
    return await orders_service.steam_top_up(dto, user_id)
