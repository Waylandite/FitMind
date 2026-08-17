import json
import logging
from collections.abc import Iterator
from uuid import uuid4

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from sqlalchemy.orm import Session

from fitmind_agent.api.dependencies import CurrentUser
from fitmind_agent.core.llm import LLMConfigurationError
from fitmind_agent.db.session import get_db_session
from fitmind_agent.schemas.chat import ChatRequest, ChatResponse, PublicChatRequest
from fitmind_agent.services.chat_service import ChatService
from fitmind_agent.services.token_usage_tracker import TokenUsageContext
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


def _authenticated_command(payload: PublicChatRequest, user_id: int) -> ChatRequest:
    return ChatRequest(**payload.model_dump(), user_id=user_id, persist_log=True)


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: PublicChatRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db_session),
) -> ChatResponse:
    command = _authenticated_command(payload, current_user.id)
    try:
        service = ChatService(db=db)
        session_id = service._resolve_session_id(command)
        session_id = session_id or service._ensure_active_session(command)
        request_id = uuid4().hex
        with TokenUsageTracker.context(
            TokenUsageContext(
                request_id=request_id,
                user_id=command.user_id,
                thread_id=command.thread_id,
                session_id=session_id,
                workflow="chat",
                node_name="chat_sync",
            )
        ):
            response = service.handle(command)
        TokenUsageTracker.aggregate_turn(
            request_id=request_id,
            user_id=command.user_id,
            thread_id=command.thread_id,
            session_id=response.session_id or session_id,
            intent_type=response.intent,
        )
        return response
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API wrapper
        raise HTTPException(status_code=500, detail=f"Chat request failed: {exc}") from exc


@router.post("/chat/stream")
def chat_stream(
    payload: PublicChatRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db_session),
) -> StreamingResponse:
    command = _authenticated_command(payload, current_user.id)
    try:
        service = ChatService(db=db)
        session_id = service._resolve_session_id(command)
        session_id = session_id or service._ensure_active_session(command)
        request_id = uuid4().hex

        def event_stream() -> Iterator[str]:
            final_intent: str | None = None
            stream_session_id = session_id
            try:
                with TokenUsageTracker.context(
                    TokenUsageContext(
                        request_id=request_id,
                        user_id=command.user_id,
                        thread_id=command.thread_id,
                        session_id=stream_session_id,
                        workflow="chat",
                        node_name="chat_stream",
                    )
                ):
                    for event in service.stream_handle(command):
                        try:
                            if event.startswith("data: "):
                                event_payload = json.loads(event[6:].strip())
                                if event_payload.get("type") == "done":
                                    final_intent = event_payload.get("intent")
                        except Exception:
                            logger.debug("Failed to inspect stream event for token aggregation.", exc_info=True)
                        yield event
            except Exception as exc:  # pragma: no cover - defensive stream wrapper
                logger.exception("Chat stream generator failed.")
                reply = f"对话流处理失败：{exc}"
                if command.persist_log and command.user_id is not None:
                    try:
                        stream_session_id = (
                            service._resolve_session_id(command)
                            or stream_session_id
                            or service._ensure_active_session(command)
                        )
                        service._persist_conversation_logs(
                            payload=command,
                            reply=reply,
                            session_id=stream_session_id,
                            db_intent_type="query",
                        )
                    except Exception:
                        logger.exception("Failed to persist stream error conversation log.")
                yield f"data: {json.dumps({'type': 'error', 'message': reply}, ensure_ascii=False)}\n\n"
            finally:
                TokenUsageTracker.aggregate_turn(
                    request_id=request_id,
                    user_id=command.user_id,
                    thread_id=command.thread_id,
                    session_id=stream_session_id,
                    intent_type=final_intent,
                )

        return StreamingResponse(
            event_stream(),
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
