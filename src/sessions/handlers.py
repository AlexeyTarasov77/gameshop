from collections.abc import Sequence
from fastapi import APIRouter, Body, status
import typing as t
from products.schemas import ProductInCartDTO, ShowProductWithRelations
from sessions.schemas import AddToCartDTO
from core.dependencies import SessionIdDep
from core.ioc import Inject
from sessions.domain.services import SessionsService
from core.schemas import Base64Int, EntityIDParam

cart_router = APIRouter(prefix="/cart", tags=["cart"])
wishlist_router = APIRouter(prefix="/wishlist", tags=["wishlist"])

SessionsServiceDep = t.Annotated[SessionsService, Inject(SessionsService)]


@wishlist_router.post("/add")
async def add_to_wishlist(
    product_id: t.Annotated[Base64Int, Body(gt=0, embed=True)],
    sessions_service: SessionsServiceDep,
    session_id: SessionIdDep,
) -> dict[str, int]:
    added = await sessions_service.wishlist_add(int(product_id), session_id)
    return {"added": added}


@wishlist_router.delete("/remove/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    product_id: EntityIDParam,
    sessions_service: SessionsServiceDep,
    session_id: SessionIdDep,
):
    await sessions_service.wishlist_remove(int(product_id), session_id)


@wishlist_router.get("/")
async def list_products_in_wishlist(
    sessions_service: SessionsServiceDep, session_id: SessionIdDep
) -> Sequence[ShowProductWithRelations]:
    return await sessions_service.wishlist_list_products(session_id)


@cart_router.post("/add")
async def add_to_cart(
    dto: AddToCartDTO, sessions_service: SessionsServiceDep, session_id: SessionIdDep
) -> dict[str, int]:
    new_qty = await sessions_service.cart_add(dto, session_id)
    return {"quantity": new_qty}


@cart_router.delete("/remove/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    product_id: EntityIDParam,
    sessions_service: SessionsServiceDep,
    session_id: SessionIdDep,
):
    await sessions_service.cart_remove(int(product_id), session_id)


@cart_router.get("/")
async def list_products_in_cart(
    sessions_service: SessionsServiceDep,
    session_id: SessionIdDep,
) -> Sequence[ProductInCartDTO]:
    return await sessions_service.cart_list_products(session_id)


@cart_router.patch("/update/{product_id}")
async def update_product_qty(
    product_id: EntityIDParam,
    qty: t.Annotated[int, Body(embed=True)],
    sessions_service: SessionsServiceDep,
    session_id: SessionIdDep,
):
    await sessions_service.cart_update_qty(int(product_id), qty, session_id)
