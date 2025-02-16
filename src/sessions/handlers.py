from collections.abc import Sequence
from fastapi import APIRouter, Body, Depends, status
import typing as t
from products.schemas import ProductInCartDTO, ShowProductWithRelations
from sessions.domain.interfaces import CartManagerFactoryI, WishlistManagerFactoryI
from sessions.schemas import AddToCartDTO
from core.dependencies import SessionIdDep
from core.ioc import Inject, Resolve
from sessions.domain.services import SessionsService
from core.schemas import Base64Int, EntityIDParam
from users.dependencies import get_optional_user_id

cart_router = APIRouter(prefix="/cart", tags=["cart"])
wishlist_router = APIRouter(prefix="/wishlist", tags=["wishlist"])


def sessions_service_factory(
    session_id: SessionIdDep,
    user_id: t.Annotated[int, Depends(get_optional_user_id)],
    cart_manager_factory: t.Annotated[CartManagerFactoryI, Inject(CartManagerFactoryI)],
    wishlist_manager_factory: t.Annotated[
        WishlistManagerFactoryI, Inject(WishlistManagerFactoryI)
    ],
) -> SessionsService:
    cart_manager = cart_manager_factory(session_id, user_id)
    wishlist_manager = wishlist_manager_factory(session_id, user_id)
    return Resolve(
        SessionsService,
        cart_manager=cart_manager,
        wishlist_manager=wishlist_manager,
    )


SessionsServiceDep = t.Annotated[SessionsService, Depends(sessions_service_factory)]


# @dataclass(frozen=True)
# class CommonHandlerDeps:
#     sessions_service: SessionsServiceDep
#     session_id: SessionIdDep
#     user_id: t.Annotated[int, Depends(get_optional_user_id)]
#
#
# CommonParamsDep = t.Annotated[CommonHandlerDeps, Depends()]
#


@wishlist_router.post("/add")
async def add_to_wishlist(
    product_id: t.Annotated[Base64Int, Body(gt=0, embed=True)],
    sessions_service: SessionsServiceDep,
) -> dict[str, int]:
    added = await sessions_service.wishlist_add(int(product_id))
    return {"added": added}


@wishlist_router.delete("/remove/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    product_id: EntityIDParam, sessions_service: SessionsServiceDep
):
    await sessions_service.wishlist_remove(int(product_id))


@wishlist_router.get("/")
async def list_products_in_wishlist(
    sessions_service: SessionsServiceDep,
) -> Sequence[ShowProductWithRelations]:
    return await sessions_service.wishlist_list_products()


@cart_router.post("/add")
async def add_to_cart(
    dto: AddToCartDTO, sessions_service: SessionsServiceDep
) -> dict[str, int]:
    new_qty = await sessions_service.cart_add(dto)
    return {"quantity": new_qty}


@cart_router.delete("/remove/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    product_id: EntityIDParam, sessions_service: SessionsServiceDep
):
    await sessions_service.cart_remove(int(product_id))


@cart_router.get("/")
async def list_products_in_cart(
    sessions_service: SessionsServiceDep,
) -> Sequence[ProductInCartDTO]:
    return await sessions_service.cart_list_products()


@cart_router.patch("/update/{product_id}")
async def update_product_qty(
    product_id: EntityIDParam,
    qty: t.Annotated[int, Body(embed=True)],
    sessions_service: SessionsServiceDep,
) -> dict[str, str]:
    action = await sessions_service.cart_update_qty(int(product_id), qty)
    return {"action": action}
