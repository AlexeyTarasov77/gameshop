from collections.abc import Sequence
from products.schemas import ProductInCartDTO, ShowProductWithRelations
from sessions.domain.interfaces import (
    CartManagerI,
    WishlistManagerI,
)
from sessions.schemas import AddToCartDTO
from core.services.base import BaseService
from core.services.exceptions import EntityNotFoundError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import NotFoundError


class SessionsService(BaseService):
    entity_name = "Product"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        cart_manager: CartManagerI,
        wishlist_manager: WishlistManagerI,
    ):
        super().__init__(uow)
        self._cart_manager = cart_manager
        self._wishlist_manager = wishlist_manager

    async def _require_product_in_stock(self, product_id: int):
        async with self._uow as uow:
            in_stock = await uow.products_repo.check_in_stock(product_id)
        if not in_stock:
            raise EntityNotFoundError(self.entity_name, id=product_id)

    async def cart_add(self, dto: AddToCartDTO) -> int:
        dto.quantity = dto.quantity or 1
        await self._require_product_in_stock(int(dto.product_id))
        is_in_cart = await self._cart_manager.check_exists(int(dto.product_id))
        if is_in_cart:
            return await self._cart_manager.add(dto)
        await self._cart_manager.create(dto)
        return dto.quantity

    async def cart_remove(self, product_id: int):
        try:
            await self._cart_manager.delete_by_id(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)

    async def cart_list_products(self) -> Sequence[ProductInCartDTO]:
        items = await self._cart_manager.list_items()
        if not items:
            return []
        async with self._uow as uow:
            products = await uow.products_repo.list_by_ids(list(items.keys()))
        res = []
        for product in products:
            product.quantity = items[product.id]  # type: ignore
            res.append(ProductInCartDTO.model_validate(product))
        return res

    async def wishlist_list_products(self) -> Sequence[ShowProductWithRelations]:
        product_ids = await self._wishlist_manager.list_ids()
        if not product_ids:
            return []
        async with self._uow as uow:
            products = await uow.products_repo.list_by_ids(product_ids)
        return [
            ShowProductWithRelations.model_validate(product) for product in products
        ]

    async def cart_update_qty(self, product_id: int, qty: int):
        try:
            if qty == 0:
                return await self._cart_manager.delete_by_id(product_id)
            return await self._cart_manager.update_qty_by_id(product_id, qty)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)

    async def wishlist_add(self, product_id: int) -> bool:
        await self._require_product_in_stock(product_id)
        is_in_wishlist = await self._wishlist_manager.check_exists(product_id)
        if not is_in_wishlist:
            await self._wishlist_manager.append(product_id)
            return True
        return False

    async def wishlist_remove(self, product_id: int):
        try:
            await self._wishlist_manager.remove(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
