from fastapi import APIRouter
from core.ioc import Inject
import typing as t

from orders.domain.services import OrdersService

router = APIRouter(prefix="/orders", tags=["orders"])

OrdersServiceDep = t.Annotated[OrdersService, Inject(OrdersService)]
