from redis.asyncio import Redis
from cart.schemas import AddToCartDTO
from core.sessions import RedisSessionManager
from gateways.db.exceptions import NotFoundError


class CartRepository(RedisSessionManager):
    def __init__(self, storage: Redis, session_key: str):
        super().__init__(storage, session_key)
        self._base_path = "$.cart"

    async def create(self, dto: AddToCartDTO):
        await super().set_to_session(
            f"{self._base_path}.{dto.product_id}", dto.quantity
        )

    async def check_exists(self, product_id: int) -> bool:
        return bool(
            await super().retrieve_from_session(f"{self._base_path}.{product_id}")
        )

    async def add(self, dto: AddToCartDTO):
        res = await self._storage.json().numincrby(
            self.storage_key,
            f"{self._base_path}.{dto.product_id}",
            dto.quantity,
        )
        if res is None:
            raise NotFoundError()

    async def delete_by_id(self, product_id: int):
        await super().delete_from_session(f"{self._base_path}.{product_id}")

    async def update_qty_by_id(self, product_id: int, qty: int):
        success = await super().set_to_session(
            f"{self._base_path}.{product_id}", qty, xx=True
        )
        if not success:
            raise NotFoundError()
