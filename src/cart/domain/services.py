from cart.domain.interfaces import CartManagerI
from cart.schemas import AddToCartDTO
from core.services.base import BaseService
from core.services.exceptions import EntityNotFoundError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import NotFoundError


class CartService(BaseService):
    entity_name = "Product"

    def __init__(
        self, uow: AbstractUnitOfWork, cart_manager_cls: type[CartManagerI]
    ):  # deliberately ommited type[] due to dependecy resolving error
        super().__init__(uow)
        self._cart_manager_cls = cart_manager_cls

    async def add_to_cart(self, dto: AddToCartDTO, session_id: str) -> int:
        dto.quantity = dto.quantity or 1
        async with self._uow as uow:
            in_stock = await uow.products_repo.check_in_stock(int(dto.product_id))
        if not in_stock:
            raise EntityNotFoundError(self.entity_name, id=dto.product_id)
        cart_manager = self._cart_manager_cls.get_for_session(session_id)
        is_in_cart = await cart_manager.check_exists(int(dto.product_id))
        if is_in_cart:
            return await cart_manager.add(dto)
        await cart_manager.create(dto)
        return dto.quantity

    async def remove_from_cart(self, product_id: int, session_id: str):
        cart_manager = self._cart_manager_cls.get_for_session(session_id)
        try:
            await cart_manager.delete_by_id(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)

    async def update_product_qty(self, product_id: int, qty: int, session_id: str):
        cart_manager = self._cart_manager_cls.get_for_session(session_id)
        try:
            if qty == 0:
                return await cart_manager.delete_by_id(product_id)
            return await cart_manager.update_qty_by_id(product_id, qty)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
