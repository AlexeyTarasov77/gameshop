from typing import Protocol


class LLMProviderI(Protocol):
    async def reply_to_user(self, message: str, user_id: int) -> str: ...
