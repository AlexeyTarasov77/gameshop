from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from chatbot.prompts import SYSTEM_PROMPT


class LLMAgent:
    def __init__(self, google_api_key: str) -> None:
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", google_api_key=google_api_key
        )
        self._llm = self._llm.bind_tools([])

    def _format_user_prompt(self, message: str, user_id: int) -> HumanMessage:
        return HumanMessage(
            content=f"""
            user_id: {user_id}
            message: {message}
            """
        )

    def _create_llm_user_input(self, message: str, user_id: int) -> LanguageModelInput:
        return [SYSTEM_PROMPT, self._format_user_prompt(message, user_id)]

    async def reply_to_user(self, message: str, user_id: int) -> str:
        res = await self._llm.ainvoke(self._create_llm_user_input(message, user_id))
        return res.text()
