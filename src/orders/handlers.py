from uuid import UUID
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from core.api.pagination import PaginatedResponse
from core.api.dependencies import PaginationDep
from core.ioc import Inject
import typing as t

from core.api.schemas import require_dto_not_empty
from orders.domain.services import OrdersService
from orders.schemas import (
    CreateInAppOrderDTO,
    CreateSteamGiftOrderDTO,
    ListOrdersForUserParamsDTO,
    ListOrdersParamsDTO,
    OrderDetailSchemaT,
    OrderPaymentDTO,
    InAppOrderDTO,
    ShowBaseOrderDTO,
    SteamGiftOrderDTO,
    SteamTopUpOrderDTO,
    CreateSteamTopUpOrderDTO,
    UpdateOrderDTO,
)
from users.dependencies import get_optional_user_id, get_user_id_or_raise, require_admin

router = APIRouter(prefix="/orders", tags=["orders"])

OrdersServiceDep = t.Annotated[OrdersService, Inject(OrdersService)]


@router.post(
    "/in-app",
    status_code=status.HTTP_201_CREATED,
)
async def create_in_app_order(
    dto: CreateInAppOrderDTO,
    user_id: t.Annotated[int | None, Depends(get_optional_user_id)],
    orders_service: OrdersServiceDep,
) -> OrderPaymentDTO[InAppOrderDTO]:
    if not (user_id or (dto.user.email and dto.user.name)):
        raise HTTPException(400, "email and name are required for not authorized user")
    return await orders_service.create_in_app_order(dto, user_id)


@router.patch("/update/{order_id}", dependencies=[Depends(require_admin)])
async def update_order(
    dto: UpdateOrderDTO, order_id: UUID, orders_service: OrdersServiceDep
) -> ShowBaseOrderDTO:
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
    dto: t.Annotated[ListOrdersParamsDTO, Query()] = None,  # type: ignore
) -> PaginatedResponse[ShowBaseOrderDTO]:
    orders, total_records = await orders_service.list_all_orders(pagination_params, dto)
    return PaginatedResponse.new_response(orders, total_records, pagination_params)


@router.get("/list-for-user")
async def list_orders_for_user(
    pagination_params: PaginationDep,
    orders_service: OrdersServiceDep,
    dto: t.Annotated[ListOrdersForUserParamsDTO, Query()] = None,  # type: ignore
    user_id: int = Depends(get_user_id_or_raise),
) -> PaginatedResponse[ShowBaseOrderDTO]:
    dto.user_id = user_id
    orders, total_records = await orders_service.list_orders_for_user(
        pagination_params, dto
    )
    return PaginatedResponse.new_response(orders, total_records, pagination_params)


@router.get("/detail/{order_id}")
async def get_order(
    order_id: UUID, orders_service: OrdersServiceDep
) -> OrderDetailSchemaT:
    return await orders_service.get_order(order_id)


@router.post("/steam/top-up")
async def steam_top_up(
    dto: CreateSteamTopUpOrderDTO,
    orders_service: OrdersServiceDep,
    user_id: int | None = Depends(get_optional_user_id),
) -> OrderPaymentDTO[SteamTopUpOrderDTO]:
    return await orders_service.create_steam_top_up_order(dto, user_id)


@router.post("/steam/gift")
async def steam_send_gift(
    dto: CreateSteamGiftOrderDTO,
    orders_service: OrdersServiceDep,
    user_id: int | None = Depends(get_optional_user_id),
) -> OrderPaymentDTO[SteamGiftOrderDTO]:
    return await orders_service.create_steam_gift_order(dto, user_id)


@router.post("/steam/top-up/fee", dependencies=[Depends(require_admin)])
async def set_steam_top_up_fee(
    percent_fee: t.Annotated[int, Body(embed=True, gt=0)],
    orders_service: OrdersServiceDep,
) -> dict[str, bool]:
    await orders_service.set_steam_top_up_fee(percent_fee)
    return {"success": True}


@router.get("/steam/top-up/fee")
async def get_steam_top_up_fee(
    orders_service: OrdersServiceDep,
) -> dict[str, int]:
    percent_fee = await orders_service.get_steam_top_up_fee()
    return {"percent_fee": percent_fee}
