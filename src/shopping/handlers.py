from collections.abc import Sequence
from fastapi import APIRouter, Body, Depends, status
import typing as t
from products.schemas import ProductInCartDTO, ShowProductExtended
from shopping.domain.interfaces import CartManagerFactoryI, WishlistManagerFactoryI
from shopping.schemas import ItemInCartDTO
from core.dependencies import SessionKeyDep
from core.ioc import Inject, Resolve
from shopping.domain.services import ShoppingService
from core.schemas import Base64Int, EntityIDParam
from users.dependencies import get_optional_user_id

cart_router = APIRouter(prefix="/cart", tags=["cart"])
wishlist_router = APIRouter(prefix="/wishlist", tags=["wishlist"])


def shopping_service_factory(
    session_key: SessionKeyDep,
    user_id: t.Annotated[int, Depends(get_optional_user_id)],
    cart_manager_factory: t.Annotated[CartManagerFactoryI, Inject(CartManagerFactoryI)],
    wishlist_manager_factory: t.Annotated[
        WishlistManagerFactoryI, Inject(WishlistManagerFactoryI)
    ],
) -> ShoppingService:
    cart_manager = cart_manager_factory.create(session_key, user_id)
    wishlist_manager = wishlist_manager_factory.create(session_key, user_id)
    return Resolve(
        ShoppingService,
        cart_manager=cart_manager,
        wishlist_manager=wishlist_manager,
    )


ShoppingServiceDep = t.Annotated[ShoppingService, Depends(shopping_service_factory)]


@wishlist_router.post("/add")
async def add_to_wishlist(
    product_id: t.Annotated[Base64Int, Body(gt=0, embed=True)],
    shopping_service: ShoppingServiceDep,
) -> dict[str, bool]:
    await shopping_service.wishlist_add(int(product_id))
    return {"success": True}


@wishlist_router.delete("/remove/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    product_id: EntityIDParam, shopping_service: ShoppingServiceDep
):
    await shopping_service.wishlist_remove(int(product_id))


@wishlist_router.get("/")
async def list_products_in_wishlist(
    shopping_service: ShoppingServiceDep,
) -> Sequence[ShowProductExtended]:
    return await shopping_service.wishlist_list_products()


@cart_router.post("/add")
async def add_to_cart(
    dto: ItemInCartDTO, shopping_service: ShoppingServiceDep
) -> dict[str, int]:
    new_qty = await shopping_service.cart_add(dto)
    return {"quantity": new_qty}


@cart_router.delete("/remove/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    product_id: EntityIDParam, shopping_service: ShoppingServiceDep
):
    await shopping_service.cart_remove(int(product_id))


@cart_router.get("/")
async def list_products_in_cart(
    shopping_service: ShoppingServiceDep,
) -> Sequence[ProductInCartDTO]:
    return await shopping_service.cart_list_products()


@cart_router.patch("/update/{product_id}")
async def update_product_qty(
    product_id: EntityIDParam,
    qty: t.Annotated[int, Body(embed=True)],
    shopping_service: ShoppingServiceDep,
) -> dict[str, str]:
    action = await shopping_service.cart_update_qty(int(product_id), qty)
    return {"action": action}
