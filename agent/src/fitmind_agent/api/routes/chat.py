from fastapi import APIRouter

from fitmind_agent.schemas.chat import ChatRequest, ChatResponse
from fitmind_agent.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    service = ChatService()
    return service.handle(payload)
