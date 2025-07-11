from logging import Logger
from chatbot.domain.interfaces import LLMProviderI
from core.services.base import BaseService
from core.uow import AbstractUnitOfWork


class ChatbotService(BaseService):
    def __init__(
        self, uow: AbstractUnitOfWork, logger: Logger, llm_provider: LLMProviderI
    ) -> None:
        super().__init__(uow, logger)
        self._llm_provider = llm_provider

    async def reply(self, message: str, user_id: int) -> str:
        return await self._llm_provider.reply_to_user(message, user_id)
