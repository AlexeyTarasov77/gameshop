import typing as t

from shopping.schemas import ItemInCartDTO


class CartManagerI(t.Protocol):
    async def add_quantity(self, dto: ItemInCartDTO) -> int: ...

    async def delete_by_id(self, product_id: int): ...

    async def update_qty_by_id(self, product_id: int, qty: int): ...

    async def create(self, dto: ItemInCartDTO): ...

    async def list_items(self) -> dict[int, int]: ...


class SessionCopierI(t.Protocol):
    """Copies anonymous data from session to authorized user's storage"""

    async def copy_for_user(self, session_key: str, user_id: int): ...


class _BaseManagerFactoryI[T](t.Protocol):
    def create(
        self, session_key: str | None = None, user_id: int | None = None
    ) -> T: ...


class CartManagerFactoryI(_BaseManagerFactoryI[CartManagerI], t.Protocol): ...


class WishlistManagerI(t.Protocol):
    async def append(self, product_id: int): ...

    async def remove(self, product_id: int): ...

    async def list_ids(self) -> t.Sequence[int]: ...


class WishlistManagerFactoryI(_BaseManagerFactoryI[WishlistManagerI], t.Protocol): ...
