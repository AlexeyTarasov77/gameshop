from collections.abc import Sequence

from redis.asyncio import Redis
from sessions.domain.interfaces import (
    CartManagerFactoryI,
    CartManagerI,
    WishlistManagerFactoryI,
    WishlistManagerI,
)
from sessions.schemas import AddToCartDTO
from sessions.sessions import RedisSessionManager
from gateways.db.exceptions import NotFoundError


def cart_manager_factory(db: Redis) -> CartManagerFactoryI:
    def create_func(
        session_key: str | None = None, user_id: int | None = None
    ) -> CartManagerI:
        assert any([session_key, user_id])
        if user_id is not None:
            return UserCartManager(db, user_id)
        return CartSessionManager(db, str(session_key))

    return create_func


def wishlist_manager_factory(db: Redis) -> WishlistManagerFactoryI:
    def create_func(
        session_key: str | None = None, user_id: int | None = None
    ) -> WishlistManagerI:
        assert any([session_key, user_id])
        if user_id is not None:
            return UserWishlistManager(db, user_id)
        return WishlistSessionManager(db, str(session_key))

    return create_func


class _BaseUserManager:
    def __init__(self, db: Redis, user_id: int, key_ending: str):
        self._user_id = user_id
        self._db = db
        self._key = f"users:{user_id}:{key_ending}"


class UserCartManager(_BaseUserManager):
    def __init__(self, db: Redis, user_id: int):
        super().__init__(db, user_id, "cart")

    async def add(self, dto: AddToCartDTO) -> int:
        assert dto.quantity
        return await self._db.hincrby(self._key, str(dto.product_id), dto.quantity)

    async def delete_by_id(self, product_id: int):
        deleted = await self._db.hdel(self._key, str(product_id))
        if not deleted:
            raise NotFoundError()

    async def update_qty_by_id(self, product_id: int, qty: int):
        if not await self.check_exists(product_id):
            raise NotFoundError()
        await self._db.hset(self._key, str(product_id), qty)

    async def check_exists(self, product_id: int) -> bool:
        return await self._db.hexists(self._key, str(product_id))

    async def create(self, dto: AddToCartDTO):
        assert dto.quantity
        await self._db.hsetnx(self._key, str(dto.product_id), dto.quantity)

    async def list_items(self) -> dict[int, int]:
        res = await self._db.hgetall(self._key)
        return {int(k): int(v) for k, v in res.items()}


class UserWishlistManager(_BaseUserManager):
    def __init__(self, db: Redis, user_id: int):
        super().__init__(db, user_id, "wishlist")

    async def append(self, product_id: int): ...

    async def remove(self, product_id: int): ...

    async def check_exists(self, product_id: int) -> bool: ...

    async def list_ids(self) -> Sequence[int]: ...


class CartSessionManager(RedisSessionManager):
    _base_json_path = "$.cart"

    async def create(self, dto: AddToCartDTO):
        await super().set_to_session(
            f"{self._base_json_path}.{dto.product_id}", dto.quantity
        )

    async def check_exists(self, product_id: int) -> bool:
        return bool(
            await super().retrieve_from_session(f"{self._base_json_path}.{product_id}")
        )

    async def add(self, dto: AddToCartDTO) -> int:
        new_qty = await self._db.json().numincrby(
            self.storage_key,
            f"{self._base_json_path}.{dto.product_id}",
            dto.quantity,
        )
        if new_qty is None:
            raise NotFoundError()
        return int(new_qty[0])

    async def delete_by_id(self, product_id: int):
        await super().delete_from_session(f"{self._base_json_path}.{product_id}")

    async def update_qty_by_id(self, product_id: int, qty: int):
        success = await super().set_to_session(
            f"{self._base_json_path}.{product_id}", qty, xx=True
        )
        if not success:
            raise NotFoundError()

    async def list_items(self) -> dict[int, int]:
        res = await super().retrieve_from_session(self._base_json_path)
        assert res is not None
        if len(res) == 0:
            return {}
        data: dict[str, int] = res[0]
        return {int(k): v for k, v in data.items()}


class WishlistSessionManager(RedisSessionManager):
    _base_json_path = "$.wishlist"

    async def append(self, product_id: int):
        await self._db.json().arrappend(  # type: ignore
            self.storage_key, f"{self._base_json_path}", product_id
        )

    async def _index_of(self, product_id: int) -> int:
        index: list[int] | None = await self._db.json().arrindex(  # type: ignore
            self.storage_key, self._base_json_path, product_id
        )
        assert index is not None
        return index[0]

    async def remove(self, product_id: int):
        index = await self._index_of(product_id)
        if index == -1:
            raise NotFoundError()
        await self._db.json().arrpop(self.storage_key, self._base_json_path, index)  # type: ignore

    async def check_exists(self, product_id: int) -> bool:
        return await self._index_of(product_id) != -1

    async def list_ids(self) -> Sequence[int]:
        res: list[list[int]] | None = await super().retrieve_from_session(
            self._base_json_path
        )
        assert res is not None
        if len(res) == 0:
            return []
        return res[0]
