from core.api.schemas import BaseDTO


class ChatbotMessage(BaseDTO):
    id: str
    content: str
    outgoing: bool


class AskChatbotResponse(BaseDTO):
    reply: ChatbotMessage
