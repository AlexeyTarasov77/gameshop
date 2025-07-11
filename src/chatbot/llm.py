from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from chatbot.tools import ChatBotToolsContainer

from chatbot.prompts import SYSTEM_PROMPT


class LLMAgent:
    def __init__(
        self, google_api_key: str, tools_container: ChatBotToolsContainer
    ) -> None:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", google_api_key=google_api_key
        )
        self._agent = create_react_agent(
            llm,
            tools_container.get_tools(),
            prompt=SYSTEM_PROMPT,
            checkpointer=InMemorySaver(),
        )

    def _create_agent_message(self, message: str, user_id: int):
        return {
            "messages": [
                HumanMessage(
                    content=f"""
            user_id: {user_id}
            message: {message}
            """
                )
            ]
        }

    async def reply_to_user(self, message: str, user_id: int) -> str:
        config: RunnableConfig = {"configurable": {"thread_id": str(user_id)}}
        res = await self._agent.ainvoke(
            self._create_agent_message(message, user_id), config
        )
        print("LLM RESPONSE", res)
        return res["messages"][-1].content
