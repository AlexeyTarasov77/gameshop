from typing import Protocol

from chatbot.schemas import ChatbotMessage


class LLMProviderI(Protocol):
    async def reply_to_user(self, message: str, user_id: int) -> str: ...
    async def get_chat_history(self, user_id: int) -> list[ChatbotMessage]: ...
