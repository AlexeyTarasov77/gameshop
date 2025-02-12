from sessions.domain.interfaces import CartManagerI, WishlistManagerI
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
        cart_manager_cls: type[CartManagerI],
        wishlist_manager_cls: type[WishlistManagerI],
    ):  # deliberately ommited type[] due to dependecy resolving error
        super().__init__(uow)
        self._cart_manager_cls = cart_manager_cls
        self._wishlist_manager_cls = wishlist_manager_cls

    async def _require_product_in_stock(self, product_id: int):
        async with self._uow as uow:
            in_stock = await uow.products_repo.check_in_stock(product_id)
        if not in_stock:
            raise EntityNotFoundError(self.entity_name, id=product_id)

    async def cart_add(self, dto: AddToCartDTO, session_id: str) -> int:
        dto.quantity = dto.quantity or 1
        await self._require_product_in_stock(int(dto.product_id))
        cart_manager = self._cart_manager_cls.get_for_session(session_id)
        is_in_cart = await cart_manager.check_exists(int(dto.product_id))
        if is_in_cart:
            return await cart_manager.add(dto)
        await cart_manager.create(dto)
        return dto.quantity

    async def cart_remove(self, product_id: int, session_id: str):
        cart_manager = self._cart_manager_cls.get_for_session(session_id)
        try:
            await cart_manager.delete_by_id(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)

    async def cart_update_qty(self, product_id: int, qty: int, session_id: str):
        cart_manager = self._cart_manager_cls.get_for_session(session_id)
        try:
            if qty == 0:
                return await cart_manager.delete_by_id(product_id)
            return await cart_manager.update_qty_by_id(product_id, qty)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)

    async def wishlist_add(self, product_id: int, session_id: str) -> bool:
        await self._require_product_in_stock(product_id)
        wishlist_manager = self._wishlist_manager_cls.get_for_session(session_id)
        is_in_wishlist = await wishlist_manager.check_exists(product_id)
        if not is_in_wishlist:
            await wishlist_manager.append(product_id)
            return True
        return False

    async def wishlist_remove(self, product_id: int, session_id: str):
        wishlist_manager = self._wishlist_manager_cls.get_for_session(session_id)
        try:
            await wishlist_manager.remove(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
