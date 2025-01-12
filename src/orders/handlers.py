from fastapi import APIRouter, Depends, HTTPException, status
from core.http.utils import EntityIDParam
from core.ioc import Inject
import typing as t

from core.service import ServiceError
from core.http.exceptions import HttpExceptionsMapper
from orders.domain.services import OrdersService, ServiceValidationError
from orders.schemas import CreateOrderDTO, BaseShowOrder, UpdateOrderDTO
from users.dependencies import get_user_id

router = APIRouter(prefix="/orders", tags=["orders"])

OrdersServiceDep = t.Annotated[OrdersService, Inject(OrdersService)]


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_order(
    dto: CreateOrderDTO,
    user_id: t.Annotated[int | None, Depends(get_user_id)],
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
