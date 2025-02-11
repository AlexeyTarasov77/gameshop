from cart.schemas import AddToCartDTO
from core.sessions import SessionManager
from gateways.db.exceptions import NotFoundError


class CartRepository:
    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager
        self._base_path = "$.cart"

    async def add(self, dto: AddToCartDTO, session_id: str):
        await self._session_manager.set_to_session(
            f"{self._base_path}.{dto.product_id}", dto.quantity, session_id
        )

    async def delete_by_id(self, product_id: int, session_id: str):
        deleted_count = await self._session_manager.delete_from_session(
            f"{self._base_path}.{product_id}", session_id
        )
        if deleted_count == 0:
            raise NotFoundError()
