from logging import Logger
from uuid import uuid4
from chatbot.domain.interfaces import LLMProviderI
from chatbot.schemas import ChatbotMessage
from core.services.base import BaseService
from core.uow import AbstractUnitOfWork


class ChatbotService(BaseService):
    def __init__(
        self, uow: AbstractUnitOfWork, logger: Logger, llm_provider: LLMProviderI
    ) -> None:
        super().__init__(uow, logger)
        self._llm_provider = llm_provider

    async def reply(self, message: str, user_id: int) -> ChatbotMessage:
        content = await self._llm_provider.reply_to_user(message, user_id)
        return ChatbotMessage(id=str(uuid4()), content=content, outgoing=False)

    async def get_chat_history(self, user_id: int) -> list[ChatbotMessage]:
        return await self._llm_provider.get_chat_history(user_id)
