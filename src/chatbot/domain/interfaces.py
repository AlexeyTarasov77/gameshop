from typing import Protocol


class LLMProvider(Protocol):
    async def reply_to_user(self, message: str, user_id: int) -> str: ...
