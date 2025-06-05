from abc import ABC, abstractmethod
import asyncio
from collections.abc import Mapping, Sequence
from core.logging import AbstractLogger

from gateways.db import RedisClient
from shopping.domain.interfaces import (
    CartManagerI,
    WishlistManagerI,
)
from shopping.schemas import ItemInCartDTO
from shopping.sessions import RedisSessionManager
from gateways.db.exceptions import AlreadyExistsError, NotFoundError


class AbstractManagerFactory[T](ABC):
    def __init__(self, db: RedisClient):
        self._db = db

    @abstractmethod
    def create(self, session_key: str | None = None, user_id: int | None = None) -> T:
        assert any([session_key, user_id])


class CartManagerFactory(AbstractManagerFactory[CartManagerI]):
    def create(self, session_key: str | None = None, user_id: int | None = None):
        super().create(session_key, user_id)
        if user_id is not None:
            return UserCartManager(self._db, user_id)
        return CartSessionManager(self._db, str(session_key))


class WishlistManagerFactory(AbstractManagerFactory[WishlistManagerI]):
    def create(self, session_key: str | None = None, user_id: int | None = None):
        super().create(session_key, user_id)
        if user_id is not None:
            return UserWishlistManager(self._db, user_id)
        return WishlistSessionManager(self._db, str(session_key))


class SessionCopier:
    def __init__(self, db: RedisClient, logger: AbstractLogger):
        self._db = db
        self._logger = logger

    async def copy_for_user(self, session_key: str, user_id: int):
        self._logger.info(
            "Copying session data",
            for_user_id=user_id,
            from_session_key=session_key,
        )
        cart_session_manager = CartSessionManager(self._db, session_key)
        wishlist_session_manager = WishlistSessionManager(self._db, session_key)
        cart_data, wishlist_data = await asyncio.gather(
            cart_session_manager.list_items(), wishlist_session_manager.list_ids()
        )
        if cart_data or wishlist_data:
            user_cart_manager = UserCartManager(self._db, user_id)
            user_wishlist_manager = UserWishlistManager(self._db, user_id)
            await asyncio.gather(
                user_cart_manager.load(cart_data),
                user_wishlist_manager.load(wishlist_data),
            )
            self._logger.info("Data has been succesfully loaded to user's storage")
        else:
            self._logger.info("Nothing to copy")


class _BaseUserManager:
    def __init__(self, db: RedisClient, user_id: int, key_ending: str):
        self._user_id = user_id
        self._db = db
        self._key = f"users:{user_id}:{key_ending}"


class UserCartManager(_BaseUserManager):
    def __init__(self, db: RedisClient, user_id: int):
        super().__init__(db, user_id, "cart")

    async def load(self, data: Mapping[int, int]):
        if data:
            await self._db.hset(self._key, mapping=data)  # type: ignore

    async def add_quantity(self, dto: ItemInCartDTO) -> int:
        return await self._db.hincrby(self._key, str(dto.product_id), dto.quantity or 1)

    async def delete_by_id(self, product_id: int):
        deleted = await self._db.hdel(self._key, str(product_id))
        if not deleted:
            raise NotFoundError()

    async def update_qty_by_id(self, product_id: int, qty: int):
        updated = await self._db.hsetnx(self._key, str(product_id), qty)
        if not updated:
            raise NotFoundError()

    async def create(self, dto: ItemInCartDTO):
        created = await self._db.hsetnx(
            self._key, str(dto.product_id), dto.quantity or 1
        )
        if not created:
            raise AlreadyExistsError()

    async def list_items(self) -> dict[int, int]:
        res = await self._db.hgetall(self._key)
        return {int(k): int(v) for k, v in res.items()}


class CartSessionManager(RedisSessionManager):
    _base_json_path = "$.cart"

    async def create(self, dto: ItemInCartDTO):
        created = await super().set_to_session(
            f"{self._base_json_path}.{dto.product_id}", dto.quantity, nx=True
        )
        if not created:
            raise AlreadyExistsError()

    async def add_quantity(self, dto: ItemInCartDTO) -> int:
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
        if res is None or len(res) == 0:
            return {}
        data: dict[str, int] = res[0]
        return {int(k): v for k, v in data.items()}


class UserWishlistManager(_BaseUserManager):
    def __init__(self, db: RedisClient, user_id: int):
        super().__init__(db, user_id, "wishlist")

    async def load(self, product_ids: Sequence[int]):
        if product_ids:
            await self._db.sadd(self._key, *product_ids)

    async def append(self, product_id: int):
        added = await self._db.sadd(self._key, product_id)
        if not added:
            raise AlreadyExistsError()

    async def remove(self, product_id: int):
        removed = await self._db.srem(self._key, product_id)
        if not removed:
            raise NotFoundError()

    async def list_ids(self) -> Sequence[int]:
        res = await self._db.smembers(self._key)
        return [int(product_id) for product_id in res]


class WishlistSessionManager(RedisSessionManager):
    _base_json_path = "$.wishlist"

    async def append(self, product_id: int):
        if await self.check_exists(product_id):
            raise AlreadyExistsError()
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
        if res is None or len(res) == 0:
            return []
        return res[0]
