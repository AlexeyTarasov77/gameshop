from core.services.base import BaseService


class ChatbotService(BaseService):
    async def reply(self, message: str, user_id: int) -> str: ...
