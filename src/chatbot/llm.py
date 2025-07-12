from logging import Logger
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pprint import pprint
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from chatbot.schemas import ChatbotMessage
from chatbot.tools import ChatBotToolsContainer

from chatbot.prompts import SYSTEM_PROMPT


class LLMAgent:
    def __init__(
        self,
        google_api_key: str,
        tools_container: ChatBotToolsContainer,
        logger: Logger,
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
        self._logger = logger

    def _create_agent_message(self, message: str):
        return {"messages": [HumanMessage(content=message)]}

    def _get_cfg(self, user_id: int) -> RunnableConfig:
        return {"configurable": {"thread_id": str(user_id)}}

    async def reply_to_user(self, message: str, user_id: int) -> str:
        res = await self._agent.ainvoke(
            self._create_agent_message(message), self._get_cfg(user_id)
        )
        pprint(res)
        return res["messages"][-1].content

    async def get_chat_history(self, user_id: int) -> list[ChatbotMessage]:
        cfg = self._get_cfg(user_id)
        print("STATE", self._agent.get_state(cfg).values)
        res: list[ChatbotMessage] = []
        raw_messages: list[BaseMessage] = self._agent.get_state(cfg).values.get(
            "messages", []
        )
        for msg in raw_messages:
            # skip tool messages
            if not isinstance(msg, (AIMessage, HumanMessage)):
                continue
            if not msg.id:
                self._logger.warning(
                    "Msg without id during retrieving chat history. Msg: %s", msg
                )
                continue
            res.append(
                ChatbotMessage(
                    id=msg.id,
                    content=str(msg.content),
                    outgoing=isinstance(msg, HumanMessage),
                )
            )
        return res
