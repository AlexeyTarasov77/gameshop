from fastapi import APIRouter, Depends, HTTPException, status
from core.http.utils import EntityIDParam
from core.pagination import PaginationDep, PaginatedResponse
from core.ioc import Inject
import typing as t

from core.service import ServiceError
from core.http.exceptions import HttpExceptionsMapper
from orders.domain.services import OrdersService, ServiceValidationError
from orders.schemas import (
    CreateOrderDTO,
    BaseShowOrder,
    UpdateOrderDTO,
    ShowOrderWithRelations,
)
from users.dependencies import get_optional_user_id, get_user_id_or_raise

router = APIRouter(prefix="/orders", tags=["orders"])

OrdersServiceDep = t.Annotated[OrdersService, Inject(OrdersService)]


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_order(
    dto: CreateOrderDTO,
    user_id: t.Annotated[int | None, Depends(get_optional_user_id)],
    orders_service: OrdersServiceDep,
) -> BaseShowOrder:
    try:
        order = await orders_service.create_order(dto, user_id)
    except ServiceValidationError as e:
        raise HTTPException(422, e.args[0])
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return order


@router.patch("/update/{order_id}")
async def update_order(
    dto: UpdateOrderDTO, order_id: EntityIDParam, orders_service: OrdersServiceDep
):
    if not dto.model_dump(exclude_unset=True):
        raise HTTPException(422, "Nothing to update. No data provided")
    try:
        order = await orders_service.update_order(dto, int(order_id))
    except ServiceValidationError as e:
        raise HTTPException(422, e.args[0])
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return order


@router.delete("/delete/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(order_id: EntityIDParam, orders_service: OrdersServiceDep):
    try:
        await orders_service.delete_order(int(order_id))
    except ServiceValidationError as e:
        raise HTTPException(422, e.args[0])
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)


class OrdersPaginatedResponse(PaginatedResponse):
    orders: list[ShowOrderWithRelations]


@router.get("/list")
async def list_all_orders(
    pagination_params: PaginationDep,
    orders_service: OrdersServiceDep,
) -> OrdersPaginatedResponse:
    try:
        orders, total_records = await orders_service.list_all_orders(pagination_params)
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return OrdersPaginatedResponse(
        orders=orders,
        total_records=total_records,
        total_on_page=len(orders),
        **pagination_params.model_dump(),
    )


@router.get("/list-for-user")
async def list_orders_for_user(
    pagination_params: PaginationDep,
    orders_service: OrdersServiceDep,
    user_id: int = Depends(get_user_id_or_raise),
):
    try:
        orders, total_records = await orders_service.list_orders_for_user(
            pagination_params, user_id
        )
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
    return OrdersPaginatedResponse(
        orders=orders,
        total_records=total_records,
        total_on_page=len(orders),
        **pagination_params.model_dump(),
    )


@router.get("/detail/{order_id}")
async def get_order(
    order_id: EntityIDParam, orders_service: OrdersServiceDep
) -> ShowOrderWithRelations:
    try:
        return await orders_service.get_order(int(order_id))
    except ServiceValidationError as e:
        raise HTTPException(422, e.args[0])
    except ServiceError as e:
        HttpExceptionsMapper.map_and_raise(e)
