import json
from collections.abc import Iterator
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from fitmind_agent.core.config import get_settings
from fitmind_agent.repositories.intent import IntentRecognitionLogRepository
from fitmind_agent.repositories.memory import ChatSessionRepository
from fitmind_agent.repositories.memory import ChatSessionSummaryRepository
from fitmind_agent.repositories.memory import ConversationLogRepository
from fitmind_agent.repositories.nutrition import NutritionRecordDraftRepository
from fitmind_agent.repositories.nutrition import BodyStatusRecordDraftRepository
from fitmind_agent.repositories.workout import WorkoutRecordDraftRepository
from fitmind_agent.repositories.workout import WorkoutPlanDraftRepository
from fitmind_agent.schemas.chat import ChatRequest, ChatResponse
from fitmind_agent.schemas.intent import IntentModuleRoute
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.schemas.llm import LLMChatRequest
from fitmind_agent.schemas.llm import LLMMessage
from fitmind_agent.services.chat_context import ConversationContextBuilder
from fitmind_agent.services.body_status_record_service import BodyStatusRecordService
from fitmind_agent.services.intent_classifier import IntentClassifier
from fitmind_agent.services.intent_router import IntentRouter
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.nutrition_record_service import NutritionRecordService
from fitmind_agent.services.session_summary_service import SessionSummaryService
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker
from fitmind_agent.services.workout_plan_service import WorkoutPlanService
from fitmind_agent.services.workout_record_service import WorkoutRecordService


PENDING_CONFIRM_KEYWORDS = ("确认", "可以", "没问题", "保存", "落库", "对的", "没错", "好的")
PENDING_CANCEL_KEYWORDS = ("取消", "不要", "作废", "先不", "不保存", "放弃")
PENDING_QUESTION_KEYWORDS = ("为什么", "怎么", "什么意思", "哪里", "吗", "？", "?")
PENDING_CORRECTION_KEYWORDS = (
    "改",
    "修改",
    "修正",
    "不是",
    "应该",
    "补充",
    "加上",
    "删",
    "去掉",
    "换成",
    "调整",
)


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
        intent_result = self._classify_with_workflow_context(payload, session_id)
        module_route = self.intent_router.route(intent_result)

        if payload.persist_log and payload.user_id is not None and self.db is not None:
            session_id = session_id or self._ensure_active_session(payload)
            pending_context = self._get_pending_workflow_context(payload, session_id)
            self._persist_intent_recognition(
                payload=payload,
                session_id=session_id,
                intent_result=intent_result,
                module_route=module_route,
            )
            if self._should_short_circuit_for_pending(pending_context, intent_result):
                reply = self._build_pending_conflict_reply(pending_context)
                self._mark_pending_interruption(pending_context, payload.message)
                self._persist_conversation_logs(
                    payload=payload,
                    reply=reply,
                    session_id=session_id,
                    db_intent_type=pending_context["db_intent_type"],
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
                    reply=reply,
                )
            nutrition_result = NutritionRecordService(
                db=self.db,
                llm_service=self.llm_service,
            ).maybe_handle(
                user_id=payload.user_id,
                session_id=session_id,
                user_query=payload.message,
                intent_result=intent_result,
            )
            if nutrition_result.handled:
                self._persist_conversation_logs(
                    payload=payload,
                    reply=nutrition_result.reply,
                    session_id=session_id,
                    db_intent_type="nutrition",
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
                    reply=nutrition_result.reply,
                )

            body_status_result = BodyStatusRecordService(
                db=self.db,
                llm_service=self.llm_service,
            ).maybe_handle(
                user_id=payload.user_id,
                session_id=session_id,
                user_query=payload.message,
                intent_result=intent_result,
            )
            if body_status_result.handled:
                self._persist_conversation_logs(
                    payload=payload,
                    reply=body_status_result.reply,
                    session_id=session_id,
                    db_intent_type="body_status",
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
                    reply=body_status_result.reply,
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

            plan_result = WorkoutPlanService(
                db=self.db,
                llm_service=self.llm_service,
            ).maybe_handle(
                user_id=payload.user_id,
                session_id=session_id,
                user_query=payload.message,
                intent_result=intent_result,
            )
            if plan_result.handled:
                self._persist_conversation_logs(
                    payload=payload,
                    reply=plan_result.reply,
                    session_id=session_id,
                    db_intent_type="plan",
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
                    reply=plan_result.reply,
                )

        request = LLMChatRequest(
            messages=self._build_messages(payload, session_id=session_id),
            model=payload.model,
            temperature=payload.temperature,
        )
        with TokenUsageTracker.scoped(workflow="chat", node_name="chat_generate"):
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

        intent_result = self._classify_with_workflow_context(payload, session_id)
        module_route = self.intent_router.route(intent_result)
        if payload.persist_log and payload.user_id is not None and self.db is not None and session_id is not None:
            pending_context = self._get_pending_workflow_context(payload, session_id)
            self._persist_intent_recognition(
                payload=payload,
                session_id=session_id,
                intent_result=intent_result,
                module_route=module_route,
            )
            if self._should_short_circuit_for_pending(pending_context, intent_result):
                reply = self._build_pending_conflict_reply(pending_context)
                self._mark_pending_interruption(pending_context, payload.message)
                self._persist_conversation_logs(
                    payload=payload,
                    reply=reply,
                    session_id=session_id,
                    db_intent_type=pending_context["db_intent_type"],
                )
                self.summary_service.schedule_session_compression(session_id)
                yield self._format_sse(
                    {
                        "type": "delta",
                        "content": reply,
                        "model": "fitmind-workflow",
                    }
                )
                yield self._format_sse(
                    {
                        "type": "done",
                        "reply": reply,
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
                            "name": pending_context["workflow"],
                            "action": "pending_conflict",
                            "draft_id": pending_context["draft"].id,
                        },
                    }
                )
                return
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
            nutrition_result = NutritionRecordService(
                db=self.db,
                llm_service=self.llm_service,
            ).maybe_handle(
                user_id=payload.user_id,
                session_id=session_id,
                user_query=payload.message,
                intent_result=intent_result,
            )
            if nutrition_result.handled:
                yield self._format_sse(
                    {
                        "type": "workflow",
                        "workflow": "nutrition_record",
                        "action": nutrition_result.action,
                        "draft_id": nutrition_result.draft_id,
                        "payload": (
                            nutrition_result.payload.model_dump(mode="json")
                            if nutrition_result.payload
                            else None
                        ),
                        "persist_result": (
                            nutrition_result.persist_result.model_dump(mode="json")
                            if nutrition_result.persist_result
                            else None
                        ),
                        "draft_actions": self._build_draft_actions(
                            workflow="nutrition_record",
                            action=nutrition_result.action,
                            draft_id=nutrition_result.draft_id,
                            payload=(
                                nutrition_result.payload.model_dump(mode="json")
                                if nutrition_result.payload
                                else None
                            ),
                        ),
                    }
                )
                self._persist_conversation_logs(
                    payload=payload,
                    reply=nutrition_result.reply,
                    session_id=session_id,
                    db_intent_type="nutrition",
                )
                self.summary_service.schedule_session_compression(session_id)
                yield self._format_sse(
                    {
                        "type": "delta",
                        "content": nutrition_result.reply,
                        "model": "fitmind-workflow",
                    }
                )
                yield self._format_sse(
                    {
                        "type": "done",
                        "reply": nutrition_result.reply,
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
                            "name": "nutrition_record",
                            "action": nutrition_result.action,
                            "draft_id": nutrition_result.draft_id,
                        },
                    }
                )
                return

            body_status_result = BodyStatusRecordService(
                db=self.db,
                llm_service=self.llm_service,
            ).maybe_handle(
                user_id=payload.user_id,
                session_id=session_id,
                user_query=payload.message,
                intent_result=intent_result,
            )
            if body_status_result.handled:
                yield self._format_sse(
                    {
                        "type": "workflow",
                        "workflow": "body_status_record",
                        "action": body_status_result.action,
                        "payload": (
                            body_status_result.payload.model_dump(mode="json")
                            if body_status_result.payload
                            else None
                        ),
                        "persist_result": (
                            body_status_result.persist_result.model_dump(mode="json")
                            if body_status_result.persist_result
                            else None
                        ),
                        "draft_actions": self._build_draft_actions(
                            workflow="body_status_record",
                            action=body_status_result.action,
                            draft_id=body_status_result.draft_id,
                            payload=(
                                body_status_result.payload.model_dump(mode="json")
                                if body_status_result.payload
                                else None
                            ),
                        ),
                    }
                )
                self._persist_conversation_logs(
                    payload=payload,
                    reply=body_status_result.reply,
                    session_id=session_id,
                    db_intent_type="body_status",
                )
                self.summary_service.schedule_session_compression(session_id)
                yield self._format_sse(
                    {
                        "type": "delta",
                        "content": body_status_result.reply,
                        "model": "fitmind-workflow",
                    }
                )
                yield self._format_sse(
                    {
                        "type": "done",
                        "reply": body_status_result.reply,
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
                            "name": "body_status_record",
                            "action": body_status_result.action,
                        },
                    }
                )
                return

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
                        "draft_actions": self._build_draft_actions(
                            workflow="workout_record",
                            action=workout_result.action,
                            draft_id=workout_result.draft_id,
                            payload=(
                                workout_result.draft_payload.model_dump(mode="json")
                                if workout_result.draft_payload
                                else None
                            ),
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

            plan_result = WorkoutPlanService(
                db=self.db,
                llm_service=self.llm_service,
            ).maybe_handle(
                user_id=payload.user_id,
                session_id=session_id,
                user_query=payload.message,
                intent_result=intent_result,
            )
            if plan_result.handled:
                yield self._format_sse(
                    {
                        "type": "workflow",
                        "workflow": "workout_plan_update",
                        "action": plan_result.action,
                        "draft_id": plan_result.draft_id,
                        "draft": (
                            plan_result.draft_payload.model_dump(mode="json")
                            if plan_result.draft_payload
                            else None
                        ),
                        "persist_result": (
                            plan_result.persist_result.model_dump(mode="json")
                            if plan_result.persist_result
                            else None
                        ),
                        "draft_actions": self._build_draft_actions(
                            workflow="workout_plan_update",
                            action=plan_result.action,
                            draft_id=plan_result.draft_id,
                            payload=(
                                plan_result.draft_payload.model_dump(mode="json")
                                if plan_result.draft_payload
                                else None
                            ),
                        ),
                    }
                )
                self._persist_conversation_logs(
                    payload=payload,
                    reply=plan_result.reply,
                    session_id=session_id,
                    db_intent_type="plan",
                )
                self.summary_service.schedule_session_compression(session_id)
                yield self._format_sse(
                    {
                        "type": "delta",
                        "content": plan_result.reply,
                        "model": "fitmind-workflow",
                    }
                )
                yield self._format_sse(
                    {
                        "type": "done",
                        "reply": plan_result.reply,
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
                            "name": "workout_plan_update",
                            "action": plan_result.action,
                            "draft_id": plan_result.draft_id,
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
            with TokenUsageTracker.scoped(workflow="chat", node_name="chat_stream"):
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

    def _classify_with_workflow_context(
        self,
        payload: ChatRequest,
        session_id: int | None,
    ) -> IntentRecognitionResult:
        pending_context = self._get_pending_workflow_context(payload, session_id)
        if pending_context is not None and self._looks_like_pending_followup(payload.message):
            return self._pending_context_to_intent(pending_context)

        intent_result = self.intent_classifier.classify(payload.message)
        if (
            pending_context is not None
            and intent_result.intent in {"unknown", "general_chat"}
            and self._looks_like_pending_correction(payload.message)
        ):
            return self._pending_context_to_intent(pending_context)

        return intent_result

    def _get_pending_workflow_context(
        self,
        payload: ChatRequest,
        session_id: int | None,
    ) -> dict | None:
        if self.db is None or payload.user_id is None or session_id is None:
            return None

        candidates = []
        for context in (
            {
                "workflow": "nutrition_record",
                "intent": "today_nutrition_record",
                "db_intent_type": "nutrition",
                "label": "饮食记录",
                "repo": NutritionRecordDraftRepository(self.db),
                "draft": NutritionRecordDraftRepository(self.db).get_latest_pending(
                    user_id=payload.user_id,
                    session_id=session_id,
                ),
            },
            {
                "workflow": "workout_record",
                "intent": "today_workout_record",
                "db_intent_type": "workout",
                "label": "训练记录",
                "repo": WorkoutRecordDraftRepository(self.db),
                "draft": WorkoutRecordDraftRepository(self.db).get_latest_pending(
                    user_id=payload.user_id,
                    session_id=session_id,
                ),
            },
            {
                "workflow": "body_status_record",
                "intent": "today_body_status_record",
                "db_intent_type": "body_status",
                "label": "身体状态记录",
                "repo": BodyStatusRecordDraftRepository(self.db),
                "draft": BodyStatusRecordDraftRepository(self.db).get_latest_pending(
                    user_id=payload.user_id,
                    session_id=session_id,
                ),
            },
            {
                "workflow": "workout_plan_update",
                "intent": "user_workout_plan_update",
                "db_intent_type": "plan",
                "label": "长期训练计划",
                "repo": WorkoutPlanDraftRepository(self.db),
                "draft": WorkoutPlanDraftRepository(self.db).get_latest_pending(
                    user_id=payload.user_id,
                    session_id=session_id,
                ),
            },
        ):
            if context["draft"] is not None:
                candidates.append(context)

        if not candidates:
            return None
        return max(candidates, key=lambda item: item["draft"].updated_at or item["draft"].created_at)

    @staticmethod
    def _looks_like_pending_followup(message: str) -> bool:
        normalized = message.strip().lower()
        return any(keyword in normalized for keyword in (
            *PENDING_CONFIRM_KEYWORDS,
            *PENDING_CANCEL_KEYWORDS,
            *PENDING_QUESTION_KEYWORDS,
            *PENDING_CORRECTION_KEYWORDS,
        ))

    @staticmethod
    def _looks_like_pending_correction(message: str) -> bool:
        normalized = message.strip().lower()
        return any(keyword in normalized for keyword in PENDING_CORRECTION_KEYWORDS)

    @staticmethod
    def _pending_context_to_intent(pending_context: dict) -> IntentRecognitionResult:
        return IntentRecognitionResult(
            intent=pending_context["intent"],
            confidence=1.0,
            source="fallback",
            reason=(
                f"当前 session 存在待确认{pending_context['label']}草稿，"
                "本轮消息按挂起工作流续接处理。"
            ),
        )

    @staticmethod
    def _should_short_circuit_for_pending(
        pending_context: dict | None,
        intent_result: IntentRecognitionResult,
    ) -> bool:
        return pending_context is not None and intent_result.intent != pending_context["intent"]

    @staticmethod
    def _build_pending_conflict_reply(pending_context: dict) -> str:
        return (
            f"当前还有一条{pending_context['label']}草稿等待处理。"
            "请先回复“确认保存”或“取消”，也可以直接告诉我要修改哪里。"
            "如果你想开始新的记录，请先取消当前草稿。"
        )

    @staticmethod
    def _mark_pending_interruption(pending_context: dict, message: str) -> None:
        draft = pending_context["draft"]
        repo = pending_context["repo"]
        old_remark = getattr(draft, "remark", None) or ""
        next_remark = f"{old_remark}\n[interrupted] {message}".strip()
        if hasattr(draft, "remark"):
            repo.update(draft, {"remark": next_remark})

    @staticmethod
    def _build_draft_actions(
        *,
        workflow: str,
        action: str,
        draft_id: int | None,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if action not in {"draft_created", "draft_updated"} or draft_id is None:
            return None

        label_map = {
            "nutrition_record": "饮食记录草稿",
            "body_status_record": "身体状态草稿",
            "workout_record": "训练记录草稿",
            "workout_plan_update": "长期训练计划草稿",
        }
        label = label_map.get(workflow, "记录草稿")
        source = payload or {}

        return {
            "label": label,
            "hint": f"请确认这条{label}：可以直接保存、取消，或点击纠正错误后修改内容再发送。",
            "confirm_text": "确认保存",
            "cancel_text": "取消保存",
            "correction_text": "纠正错误",
            "correction_prefill": (
                f"请修改这条{label}，下面是当前提取结果：\n"
                f"{json.dumps(source, ensure_ascii=False, indent=2, default=str)}"
            ),
        }

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
