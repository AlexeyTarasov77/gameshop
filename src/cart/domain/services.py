from cart.domain.interfaces import CartRepositoryI
from cart.schemas import AddToCartDTO
from core.services.base import BaseService
from core.services.exceptions import EntityNotFoundError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import NotFoundError


class CartService(BaseService):
    entity_name = "Product"

    def __init__(self, uow: AbstractUnitOfWork, cart_repository: CartRepositoryI):
        super().__init__(uow)
        self._cart_repository = cart_repository

    async def add_to_cart(self, dto: AddToCartDTO, session_id: str):
        not_found_err = EntityNotFoundError(self.entity_name, id=dto.product_id)
        try:
            async with self._uow as uow:
                in_stock = await uow.products_repo.check_in_stock(int(dto.product_id))
                if not in_stock:
                    raise not_found_err
        except NotFoundError:
            raise not_found_err
        await self._cart_repository.add(dto, session_id)

    async def remove_from_cart(self, product_id: int, session_id: str):
        try:
            await self._cart_repository.delete_by_id(product_id, session_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
