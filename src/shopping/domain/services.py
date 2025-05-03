from collections.abc import Sequence
from logging import Logger
from typing import Literal
from products.schemas import ProductInCartDTO, ShowProductExtended
from shopping.domain.interfaces import (
    CartManagerI,
    WishlistManagerI,
)
from shopping.schemas import ItemInCartDTO
from core.services.base import BaseService
from core.services.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import AlreadyExistsError, NotFoundError


class ShoppingService(BaseService):
    entity_name = "Product"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        logger: Logger,
        cart_manager: CartManagerI,
        wishlist_manager: WishlistManagerI,
    ):
        super().__init__(uow, logger)
        self._cart_manager = cart_manager
        self._wishlist_manager = wishlist_manager

    async def _require_product_in_stock(self, product_id: int):
        async with self._uow() as uow:
            in_stock = await uow.products_repo.check_in_stock(product_id)
        if not in_stock:
            raise EntityNotFoundError(self.entity_name, id=product_id)

    async def cart_add(self, dto: ItemInCartDTO) -> int:
        dto.quantity = dto.quantity or 1
        await self._require_product_in_stock(int(dto.product_id))
        try:
            await self._cart_manager.create(dto)
        except AlreadyExistsError:
            return await self._cart_manager.add_quantity(dto)
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
        async with self._uow() as uow:
            products = await uow.products_repo.list_by_ids(list(items.keys()))
        res = []
        for product in products:
            product.quantity = items[product.id]  # type: ignore
            res.append(ProductInCartDTO.model_validate(product))
        return res

    async def wishlist_list_products(self) -> Sequence[ShowProductExtended]:
        product_ids = await self._wishlist_manager.list_ids()
        if not product_ids:
            return []
        async with self._uow() as uow:
            products = await uow.products_repo.list_by_ids(product_ids)
        return [ShowProductExtended.model_validate(product) for product in products]

    async def cart_update_qty(
        self, product_id: int, qty: int
    ) -> Literal["updated", "deleted"]:
        try:
            if qty == 0:
                await self._cart_manager.delete_by_id(product_id)
                return "deleted"
            await self._cart_manager.update_qty_by_id(product_id, qty)
            return "updated"
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)

    async def wishlist_add(self, product_id: int):
        await self._require_product_in_stock(product_id)
        try:
            await self._wishlist_manager.append(product_id)
        except AlreadyExistsError:
            raise EntityAlreadyExistsError(self.entity_name)

    async def wishlist_remove(self, product_id: int):
        try:
            await self._wishlist_manager.remove(product_id)
        except NotFoundError:
            raise EntityNotFoundError(self.entity_name, id=product_id)
