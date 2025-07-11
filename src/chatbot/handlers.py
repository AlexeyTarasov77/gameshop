from fastapi import APIRouter, Body, Depends
import typing as t
from chatbot.domain.services import ChatbotService
from core.ioc import Inject
from users.dependencies import get_user_id_or_raise


router = APIRouter(prefix="/chatbot", tags=["chatbox", "ai"])

ChatbotServiceDep = t.Annotated[ChatbotService, Inject(ChatbotService)]


@router.post("/ask")
async def ask_chatbot(
    service: ChatbotServiceDep,
    message: t.Annotated[str, Body(embed=True)],
    user_id: t.Annotated[int, Depends(get_user_id_or_raise)],
):
    reply = await service.reply(message, user_id)
    return {"reply": reply}
