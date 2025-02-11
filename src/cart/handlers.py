from fastapi import APIRouter, status
import typing as t
from cart.schemas import AddToCartDTO
from core.dependencies import SessionIdDep
from core.ioc import Inject
from cart.domain.services import CartService
from core.schemas import EntityIDParam

router = APIRouter(prefix="/cart", tags=["cart"])

CartServiceDep = t.Annotated[CartService, Inject(CartService)]


@router.post("/add", status_code=status.HTTP_204_NO_CONTENT)
async def add_to_cart(
    dto: AddToCartDTO, cart_service: CartServiceDep, session_id: SessionIdDep
) -> None:
    await cart_service.add_to_cart(dto, session_id)


@router.delete("/remove/{product_id}")
async def remove_from_cart(
    product_id: EntityIDParam, cart_service: CartServiceDep, session_id: SessionIdDep
):
    await cart_service.remove_from_cart(product_id, session_id)
