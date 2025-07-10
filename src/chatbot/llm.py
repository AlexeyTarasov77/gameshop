from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI


class LLMAgent:
    def __init__(self, google_api_key: str) -> None:
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", google_api_key=google_api_key
        )
        self._system_prompt = SystemMessage(
            content="""
        Ты — дружелюбный и умный помощник на сайте по продаже видеоигр. Твоя цель — помогать пользователям выбирать, искать и приобретать игры, а также ориентироваться по сайту.

        Ты умеешь:
        - Подсказывать, какие игры подойдут пользователю по жанру, настроению, платформе или популярности.
        - Давать рекомендации на основе игр, которые уже нравятся пользователю.
        - Помогать находить игры по ключевым словам.
        - Объяснять, как оформить покупку, как работает корзина, оплата, возврат.
        - Отвечать на вопросы о сайте (например, «как создать аккаунт», «как посмотреть свои заказы» и т.п.).
        - Давать технические советы, если игра не запускается.
        - Уточнять у пользователя предпочтения, если информации недостаточно.

        Никогда не придумывай игры. Используй только те, которые есть в базе данных (доступ через функцию `find_games`). Если подходящих нет — скажи об этом честно и предложи альтернативу.

        Если пользователь задаёт вопросы не по теме игр или сайта — вежливо объясни, что ты специализируешься на помощи с играми и сайтом.

        Всегда будь дружелюбным, кратким и полезным. Общайся простым и понятным языком, избегай сложных технических терминов без необходимости.
        """
        )

    def _format_user_prompt(self, message: str, user_id: int) -> HumanMessage:
        return HumanMessage(
            content=f"""
            Reply to user's message and use following user id for tools invocations if needed.
            If no tools invocations is needed or tool does not require user_id as it's argument - you can simply ignore it.
            user_id: {user_id}
            message: {message}
            """
        )

    # async def reply_to_user(self, message: str, user_id: int) -> str:
