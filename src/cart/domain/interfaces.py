import typing as t

from cart.schemas import AddToCartDTO


class CartRepositoryI(t.Protocol):
    async def add(self, dto: AddToCartDTO, session_id: str): ...

    async def delete_by_id(self, product_id: int, session_id: str): ...

    async def update_qty_by_id(self, product_id: int, qty: int, session_id: str): ...
