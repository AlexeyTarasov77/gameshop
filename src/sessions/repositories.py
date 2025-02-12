from sessions.schemas import AddToCartDTO
from sessions.sessions import RedisSessionManager
from gateways.db.exceptions import NotFoundError


class CartRepository(RedisSessionManager):
    _base_path = "$.cart"

    async def create(self, dto: AddToCartDTO):
        await super().set_to_session(
            f"{self._base_path}.{dto.product_id}", dto.quantity
        )

    async def check_exists(self, product_id: int) -> bool:
        return bool(
            await super().retrieve_from_session(f"{self._base_path}.{product_id}")
        )

    async def add(self, dto: AddToCartDTO) -> int:
        new_qty = await self._storage.json().numincrby(
            self.storage_key,
            f"{self._base_path}.{dto.product_id}",
            dto.quantity,
        )
        if new_qty is None:
            raise NotFoundError()
        return int(new_qty[0])

    async def delete_by_id(self, product_id: int):
        await super().delete_from_session(f"{self._base_path}.{product_id}")

    async def update_qty_by_id(self, product_id: int, qty: int):
        success = await super().set_to_session(
            f"{self._base_path}.{product_id}", qty, xx=True
        )
        if not success:
            raise NotFoundError()


class WishlistRepository(RedisSessionManager):
    _base_path = "$.wishlist"

    async def append(self, product_id: int):
        await self._storage.json().arrappend(  # type: ignore
            self.storage_key, f"{self._base_path}", product_id
        )

    async def _index_of(self, product_id: int) -> int:
        index: list[int] | None = await self._storage.json().arrindex(  # type: ignore
            self.storage_key, self._base_path, product_id
        )
        assert index is not None
        return index[0]

    async def remove(self, product_id: int):
        index = await self._index_of(product_id)
        if index == -1:
            raise NotFoundError()
        await self._storage.json().arrpop(self.storage_key, self._base_path, index)  # type: ignore

    async def check_exists(self, product_id: int) -> bool:
        return await self._index_of(product_id) != -1
