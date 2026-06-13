import json
from collections.abc import Iterator
from datetime import date
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from fitmind_agent.core.config import get_settings
from fitmind_agent.repositories.intent import IntentRecognitionLogRepository
from fitmind_agent.repositories.memory import ChatSessionRepository
from fitmind_agent.repositories.memory import ChatSessionSummaryRepository
from fitmind_agent.repositories.memory import ConversationLogRepository
from fitmind_agent.schemas.chat import ChatRequest, ChatResponse
from fitmind_agent.schemas.intent import IntentModuleRoute
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.schemas.llm import LLMChatRequest
from fitmind_agent.schemas.llm import LLMMessage
from fitmind_agent.services.chat_context import ConversationContextBuilder
from fitmind_agent.services.intent_classifier import IntentClassifier
from fitmind_agent.services.intent_router import IntentRouter
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.session_summary_service import SessionSummaryService
from fitmind_agent.services.workout_record_service import WorkoutRecordService


class ChatService:
    def __init__(self, db: Session | None = None, llm_service: LLMService | None = None) -> None:
        settings = get_settings()
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.intent_classifier = IntentClassifier(llm_service=self.llm_service)
        self.intent_router = IntentRouter()
        self.context_builder = (
            ConversationContextBuilder(
                ConversationLogRepository(db),
                ChatSessionSummaryRepository(db),
                recent_context_rounds=settings.recent_context_rounds,
            )
            if db is not None
            else None
        )
        self.summary_service = SessionSummaryService(llm_service=self.llm_service)

    def handle(self, payload: ChatRequest) -> ChatResponse:
        session_id = self._resolve_session_id(payload)
        intent_result = self.intent_classifier.classify(payload.message)
        module_route = self.intent_router.route(intent_result)

        if payload.persist_log and payload.user_id is not None and self.db is not None:
            session_id = session_id or self._ensure_active_session(payload)
            self._persist_intent_recognition(
                payload=payload,
                session_id=session_id,
                intent_result=intent_result,
                module_route=module_route,
            )
            workout_result = WorkoutRecordService(
                db=self.db,
                llm_service=self.llm_service,
            ).maybe_handle(
                user_id=payload.user_id,
                session_id=session_id,
                user_query=payload.message,
                intent_result=intent_result,
            )
            if workout_result.handled:
                self._persist_conversation_logs(
                    payload=payload,
                    reply=workout_result.reply,
                    session_id=session_id,
                    db_intent_type="workout",
                )
                self.summary_service.schedule_session_compression(session_id)
                return ChatResponse(
                    user_id=payload.user_id,
                    thread_id=payload.thread_id,
                    session_id=session_id,
                    intent=intent_result.intent,
                    intent_confidence=intent_result.confidence,
                    intent_source=intent_result.source,
                    module_name=module_route.module_name,
                    module_status=module_route.status,
                    model="fitmind-workflow",
                    reply=workout_result.reply,
                )

        request = LLMChatRequest(
            messages=self._build_messages(payload, session_id=session_id),
            model=payload.model,
            temperature=payload.temperature,
        )
        llm_result = self.llm_service.generate(request)

        if payload.persist_log and payload.user_id is not None and self.db is not None:
            session_id = self._persist_conversation(
                payload=payload,
                reply=llm_result.content,
                session_id=session_id,
                db_intent_type=module_route.db_intent_type,
            )
            self.summary_service.schedule_session_compression(session_id)

        return ChatResponse(
            user_id=payload.user_id,
            thread_id=payload.thread_id,
            session_id=session_id,
            intent=intent_result.intent,
            intent_confidence=intent_result.confidence,
            intent_source=intent_result.source,
            module_name=module_route.module_name,
            module_status=module_route.status,
            model=llm_result.model,
            reply=llm_result.content,
        )

    def stream_handle(self, payload: ChatRequest) -> Iterator[str]:
        session_id = self._resolve_session_id(payload)
        if payload.persist_log and payload.user_id is not None and self.db is not None:
            session_id = session_id or self._ensure_active_session(payload)

        intent_result = self.intent_classifier.classify(payload.message)
        module_route = self.intent_router.route(intent_result)
        if payload.persist_log and payload.user_id is not None and self.db is not None and session_id is not None:
            self._persist_intent_recognition(
                payload=payload,
                session_id=session_id,
                intent_result=intent_result,
                module_route=module_route,
            )
        yield self._format_sse(
            {
                "type": "intent",
                "intent": intent_result.intent,
                "confidence": intent_result.confidence,
                "source": intent_result.source,
                "reason": intent_result.reason,
                "module": {
                    "name": module_route.module_name,
                    "status": module_route.status,
                    "description": module_route.description,
                },
            }
        )

        if payload.persist_log and payload.user_id is not None and self.db is not None:
            yield self._format_sse(
                {
                    "type": "session",
                    "thread_id": payload.thread_id,
                    "session_id": session_id,
                }
            )
            workout_result = WorkoutRecordService(
                db=self.db,
                llm_service=self.llm_service,
            ).maybe_handle(
                user_id=payload.user_id,
                session_id=session_id,
                user_query=payload.message,
                intent_result=intent_result,
            )
            if workout_result.handled:
                yield self._format_sse(
                    {
                        "type": "workflow",
                        "workflow": "workout_record",
                        "action": workout_result.action,
                        "draft_id": workout_result.draft_id,
                        "draft": (
                            workout_result.draft_payload.model_dump(mode="json")
                            if workout_result.draft_payload
                            else None
                        ),
                        "persist_result": (
                            workout_result.persist_result.model_dump(mode="json")
                            if workout_result.persist_result
                            else None
                        ),
                    }
                )
                self._persist_conversation_logs(
                    payload=payload,
                    reply=workout_result.reply,
                    session_id=session_id,
                    db_intent_type="workout",
                )
                self.summary_service.schedule_session_compression(session_id)
                yield self._format_sse(
                    {
                        "type": "delta",
                        "content": workout_result.reply,
                        "model": "fitmind-workflow",
                    }
                )
                yield self._format_sse(
                    {
                        "type": "done",
                        "reply": workout_result.reply,
                        "model": "fitmind-workflow",
                        "thread_id": payload.thread_id,
                        "session_id": session_id,
                        "intent": intent_result.intent,
                        "intent_confidence": intent_result.confidence,
                        "intent_source": intent_result.source,
                        "module": {
                            "name": module_route.module_name,
                            "status": module_route.status,
                        },
                        "workflow": {
                            "name": "workout_record",
                            "action": workout_result.action,
                        },
                    }
                )
                return

        request = LLMChatRequest(
            messages=self._build_messages(payload, session_id=session_id),
            model=payload.model,
            temperature=payload.temperature,
        )

        reply_parts: list[str] = []
        resolved_model = payload.model

        try:
            for chunk, model_name in self.llm_service.stream(request):
                reply_parts.append(chunk)
                if model_name:
                    resolved_model = model_name
                yield self._format_sse(
                    {
                        "type": "delta",
                        "content": chunk,
                        "model": resolved_model,
                    }
                )

            full_reply = "".join(reply_parts)
            if payload.persist_log and payload.user_id is not None and self.db is not None and session_id is not None:
                self._persist_conversation_logs(
                    payload=payload,
                    reply=full_reply,
                    session_id=session_id,
                    db_intent_type=module_route.db_intent_type,
                )
                self.summary_service.schedule_session_compression(session_id)

            yield self._format_sse(
                {
                    "type": "done",
                    "reply": full_reply,
                    "model": resolved_model,
                    "thread_id": payload.thread_id,
                    "session_id": session_id,
                    "intent": intent_result.intent,
                    "intent_confidence": intent_result.confidence,
                    "intent_source": intent_result.source,
                    "module": {
                        "name": module_route.module_name,
                        "status": module_route.status,
                    },
                }
            )
        except Exception as exc:
            yield self._format_sse(
                {
                    "type": "error",
                    "message": str(exc),
                }
            )
            return

    def _build_messages(self, payload: ChatRequest, session_id: int | None = None) -> list[LLMMessage]:
        if self.context_builder is None:
            messages: list[LLMMessage] = []
            if payload.system_prompt:
                messages.append(LLMMessage(role="system", content=payload.system_prompt))
            messages.append(LLMMessage(role="user", content=payload.message))
            return messages
        return self.context_builder.build_messages(payload, session_id=session_id)

    @staticmethod
    def _format_sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def _resolve_session_id(self, payload: ChatRequest) -> int | None:
        if self.db is None or payload.user_id is None:
            return None

        session_repo = ChatSessionRepository(self.db)
        chat_session = session_repo.get_latest_by_thread(
            user_id=payload.user_id,
            thread_id=payload.thread_id,
        )
        if chat_session is None or chat_session.status != "active":
            return None
        return chat_session.id

    def _ensure_active_session(self, payload: ChatRequest) -> int:
        assert self.db is not None
        assert payload.user_id is not None

        session_repo = ChatSessionRepository(self.db)
        chat_session = session_repo.get_latest_by_thread(
            user_id=payload.user_id,
            thread_id=payload.thread_id,
        )
        if chat_session is None or chat_session.status != "active":
            chat_session = session_repo.create_next_for_thread(
                user_id=payload.user_id,
                thread_id=payload.thread_id,
                title=payload.message[:40],
            )

        session_repo.update(chat_session, {"last_message_at": datetime.now()})
        return chat_session.id

    def _persist_conversation(
        self,
        payload: ChatRequest,
        reply: str,
        session_id: int | None = None,
        db_intent_type: str = "query",
    ) -> int:
        session_id = session_id or self._ensure_active_session(payload)
        self._persist_conversation_logs(
            payload=payload,
            reply=reply,
            session_id=session_id,
            db_intent_type=db_intent_type,
        )
        return session_id

    def _persist_conversation_logs(
        self,
        payload: ChatRequest,
        reply: str,
        session_id: int,
        db_intent_type: str = "query",
    ) -> None:
        assert self.db is not None
        assert payload.user_id is not None

        log_repo = ConversationLogRepository(self.db)
        log_repo.create(
            user_id=payload.user_id,
            thread_id=payload.thread_id,
            session_id=session_id,
            role="user",
            message_text=payload.message,
            record_date=date.today(),
            intent_type=db_intent_type,
        )
        log_repo.create(
            user_id=payload.user_id,
            thread_id=payload.thread_id,
            session_id=session_id,
            role="assistant",
            message_text=reply,
            record_date=date.today(),
            intent_type=db_intent_type,
        )
        self._refresh_session_activity(session_id=session_id, message_text=payload.message)

    def _persist_intent_recognition(
        self,
        *,
        payload: ChatRequest,
        session_id: int,
        intent_result: IntentRecognitionResult,
        module_route: IntentModuleRoute,
    ) -> None:
        assert self.db is not None
        assert payload.user_id is not None

        keyword_match = intent_result.keyword_match
        IntentRecognitionLogRepository(self.db).create(
            {
                "user_id": payload.user_id,
                "thread_id": payload.thread_id,
                "session_id": session_id,
                "message_text": payload.message,
                "final_intent": intent_result.intent,
                "confidence_score": Decimal(str(round(intent_result.confidence, 3))),
                "source": intent_result.source,
                "reason": intent_result.reason,
                "keyword_intent": keyword_match.intent if keyword_match else None,
                "keyword_confidence": (
                    Decimal(str(round(keyword_match.confidence, 3))) if keyword_match else None
                ),
                "matched_keywords": keyword_match.matched_keywords if keyword_match else None,
                "module_name": module_route.module_name,
                "module_status": module_route.status,
                "db_intent_type": module_route.db_intent_type,
            }
        )

    def _refresh_session_activity(self, session_id: int, message_text: str) -> None:
        assert self.db is not None

        session_repo = ChatSessionRepository(self.db)
        chat_session = session_repo.get_by_id(session_id)
        if chat_session is None:
            return

        update_payload = {"last_message_at": datetime.now()}
        normalized_title = (chat_session.title or "").strip()
        if not normalized_title or normalized_title == "新的会话":
            update_payload["title"] = message_text[:40]

        session_repo.update(chat_session, update_payload)
