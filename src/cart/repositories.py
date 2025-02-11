from cart.schemas import AddToCartDTO
from core.sessions import SessionManager


class CartRepository:
    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager

    async def add(self, dto: AddToCartDTO, session_id: str):
        await self._session_manager.update_session(
            f"$.cart.{dto.product_id}", dto.quantity, session_id
        )
