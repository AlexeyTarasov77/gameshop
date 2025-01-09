from fastapi import APIRouter, Depends, HTTPException, status
from core.ioc import Inject
import typing as t

from core.service import ServiceError
from core.http.exceptions import HttpExceptionsMapper
from orders.domain.services import OrdersService, ServiceValidationError
from orders.schemas import CreateOrderDTO, BaseShowOrder
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
