from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from sqlalchemy.orm import Session

from fitmind_agent.core.llm import LLMConfigurationError
from fitmind_agent.db.session import get_db_session
from fitmind_agent.schemas.chat import ChatRequest, ChatResponse
from fitmind_agent.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db_session)) -> ChatResponse:
    try:
        service = ChatService(db=db)
        return service.handle(payload)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API wrapper
        raise HTTPException(status_code=500, detail=f"Chat request failed: {exc}") from exc


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest, db: Session = Depends(get_db_session)) -> StreamingResponse:
    try:
        service = ChatService(db=db)
        return StreamingResponse(
            service.stream_handle(payload),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API wrapper
        raise HTTPException(status_code=500, detail=f"Chat stream failed: {exc}") from exc
