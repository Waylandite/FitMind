"""Integration coverage for clarification boundaries (service, SSE and HTTP)."""

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fitmind_agent.api.app import create_app
from fitmind_agent.db.models import Base, ChatSession, ConversationLog, IntentClarification, User
from fitmind_agent.db.session import get_db_session
from fitmind_agent.repositories.memory import ConversationLogRepository
from fitmind_agent.repositories.workout import WorkoutRecordDraftRepository
from fitmind_agent.schemas.chat import ChatRequest, ClarificationInput
from fitmind_agent.schemas.intent import IntentCandidate, IntentRecognitionResult
from fitmind_agent.services.today_workout_recommendation_service import (
    TodayWorkoutRecommendationResult,
)
from fitmind_agent.services.chat_service import ChatService
from fitmind_agent.services.intent_clarification_service import IntentClarificationService


def setup():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(email="integration@example.com", username="integration", password_hash="x")
    db.add(user)
    db.commit()
    chat = ChatSession(user_id=user.id, thread_id="integration")
    db.add(chat)
    db.commit()
    return db, user, chat


def unknown():
    return IntentRecognitionResult(intent="unknown", confidence=0, source="fallback")


def recommendation_candidate():
    return IntentRecognitionResult(
        intent="today_workout_recommendation",
        confidence=0.1,
        source="fallback",
        candidates=[IntentCandidate(intent="today_workout_recommendation", confidence=0.1)],
    )


def events(service, request):
    return [
        json.loads(item[6:]) for item in service.stream_handle(request) if item.startswith("data: ")
    ]


def test_integration_stream_requested_sse_done_awaiting_user():
    db, user, chat = setup()
    service = ChatService(db=db)
    service.intent_classifier.classify = lambda *a, **k: unknown()
    result = events(
        service,
        ChatRequest(user_id=user.id, thread_id=chat.thread_id, message="记录", persist_log=True),
    )
    assert any(event["type"] == "clarification" for event in result)
    assert result[-1]["workflow"]["action"] == "awaiting_user"


class FakeLLM:
    def generate(self, request):
        from fitmind_agent.schemas.llm import LLMChatResponse

        return LLMChatResponse(model="test", content="ok", raw_response={})


def override_session(db):
    def dependency():
        yield db

    return dependency


def test_integration_stream_cancel_done_cancelled():
    db, user, chat = setup()
    record = IntentClarificationService(db).create(
        user_id=user.id, session_id=chat.id, query="记录", result=unknown()
    )
    result = events(
        ChatService(db=db),
        ChatRequest(
            user_id=user.id,
            thread_id=chat.thread_id,
            message="取消",
            persist_log=True,
            clarification=ClarificationInput(id=record.id, action="cancel"),
        ),
    )
    assert result[-1]["workflow"]["action"] == "cancelled"


def test_integration_stream_invalid_done_terminal():
    db, user, chat = setup()
    result = events(
        ChatService(db=db),
        ChatRequest(
            user_id=user.id,
            thread_id=chat.thread_id,
            message="选择",
            persist_log=True,
            clarification=ClarificationInput(id=999, action="cancel"),
        ),
    )
    assert result[-1]["workflow"]["action"] == "invalid_terminal"


def test_integration_cross_user_does_not_resolve():
    db, user, chat = setup()
    record = IntentClarificationService(db).create(
        user_id=user.id, session_id=chat.id, query="记录", result=unknown()
    )
    other_user = User(email="other@example.com", username="other", password_hash="x")
    db.add(other_user)
    db.commit()

    result = events(
        ChatService(db=db),
        ChatRequest(
            user_id=other_user.id,
            thread_id="other-thread",
            message="选择",
            persist_log=True,
            clarification=ClarificationInput(
                id=record.id,
                action="select",
                selected_intent="today_workout_record",
            ),
        ),
    )
    db.refresh(record)

    assert result[-1]["workflow"]["action"] == "invalid_terminal"
    assert record.status == "pending"


def test_integration_active_clarification_http_protocol():
    db, user, chat = setup()
    IntentClarificationService(db).create(
        user_id=user.id, session_id=chat.id, query="记录", result=unknown()
    )
    app = create_app()
    app.dependency_overrides[get_db_session] = override_session(db)
    response = TestClient(app).get(
        f"/api/v1/memories/sessions/{chat.id}/clarification?user_id={user.id}"
    )
    assert response.status_code == 200 and response.json()["type"] == "clarification"


def test_integration_active_clarification_http_empty_protocol():
    db, user, chat = setup()
    app = create_app()
    app.dependency_overrides[get_db_session] = override_session(db)
    assert (
        TestClient(app)
        .get(f"/api/v1/memories/sessions/{chat.id}/clarification?user_id={user.id}")
        .json()
        is None
    )


def test_integration_request_rejects_forged_original_message():
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"message": "真实", "original_message": "伪造"})


def test_integration_free_text_uses_dedicated_classifier_spy():
    db, user, chat = setup()
    record = IntentClarificationService(db).create(
        user_id=user.id,
        session_id=chat.id,
        query="原始",
        result=IntentRecognitionResult(intent="general_chat", confidence=0.1, source="fallback"),
    )
    service = ChatService(db=db, llm_service=FakeLLM())
    called = []
    service.intent_classifier.classify_clarification = lambda *args: (
        called.append(args) or unknown()
    )
    service._maybe_handle_intent_clarification(
        payload=ChatRequest(user_id=user.id, thread_id=chat.thread_id, message="饮食"),
        session_id=chat.id,
        intent_result=unknown(),
    )
    assert called[0][0] == record.original_query and called[0][2] == "饮食"


def test_integration_policy_context_current_query_is_separate():
    db, user, chat = setup()
    service = ChatService(db=db)
    captured = []
    service.intent_classifier.classify = lambda query, context="": (
        captured.append((query, context)) or unknown()
    )
    service._classify_with_workflow_context(
        ChatRequest(user_id=user.id, thread_id=chat.thread_id, message="当前输入"), chat.id
    )
    assert captured[0][0] == "当前输入"


def test_integration_stream_resolved_enters_target_workflow_with_original_query(monkeypatch):
    db, user, chat = setup()
    record = IntentClarificationService(db).create(
        user_id=user.id, session_id=chat.id, query="原始训练", result=recommendation_candidate()
    )
    service = ChatService(db=db, llm_service=FakeLLM())
    captured = []

    def fake_recommendation(self, *, user_query, **kwargs):
        captured.append(user_query)
        yield {
            "kind": "result",
            "result": TodayWorkoutRecommendationResult(True, "recommended", "ok"),
        }

    monkeypatch.setattr(
        "fitmind_agent.services.chat_service.TodayWorkoutRecommendationService.stream_maybe_handle",
        fake_recommendation,
    )
    data = events(
        service,
        ChatRequest(
            user_id=user.id,
            thread_id=chat.thread_id,
            message="选择",
            persist_log=True,
            clarification=ClarificationInput(
                id=record.id, action="select", selected_intent="today_workout_recommendation"
            ),
        ),
    )
    resolve_index = next(
        i for i, item in enumerate(data) if item.get("node") == "resolve_clarification"
    )
    clarification_index = next(
        i
        for i, item in enumerate(data)
        if item["type"] == "clarification" and item["action"] == "resolved"
    )
    done_index = next(
        i
        for i, item in enumerate(data)
        if item["type"] == "done" and item["workflow"]["name"] == "today_workout_recommendation"
    )
    assert resolve_index < clarification_index < done_index
    assert captured == ["原始训练"]


def test_integration_sync_resolved_returns_terminal_payload_and_original_query(monkeypatch):
    db, user, chat = setup()
    record = IntentClarificationService(db).create(
        user_id=user.id, session_id=chat.id, query="原始训练", result=recommendation_candidate()
    )
    service = ChatService(db=db, llm_service=FakeLLM())
    captured = []

    def fake_recommendation(self, *, user_query, **kwargs):
        captured.append(user_query)
        yield {
            "kind": "result",
            "result": TodayWorkoutRecommendationResult(True, "recommended", "ok"),
        }

    monkeypatch.setattr(
        "fitmind_agent.services.chat_service.TodayWorkoutRecommendationService.stream_maybe_handle",
        fake_recommendation,
    )
    response = service.handle(
        ChatRequest(
            user_id=user.id,
            thread_id=chat.thread_id,
            message="选择",
            persist_log=True,
            clarification=ClarificationInput(
                id=record.id, action="select", selected_intent="today_workout_recommendation"
            ),
        )
    )
    assert response.clarification and response.clarification["status"] == "resolved"
    assert response.clarification["action"] == "resolved" and captured == ["原始训练"]
    assert (
        db.query(ConversationLog)
        .filter_by(role="user")
        .order_by(ConversationLog.id.desc())
        .first()
        .message_text
        == "选择"
    )


def test_integration_free_text_resolved_combines_query_and_enters_target_workflow(monkeypatch):
    db, user, chat = setup()
    record = IntentClarificationService(db).create(
        user_id=user.id,
        session_id=chat.id,
        query="原始",
        result=recommendation_candidate(),
    )
    service = ChatService(db=db, llm_service=FakeLLM())
    service.intent_classifier.classify = lambda *a, **k: unknown()
    classifier_calls = []
    captured_queries = []

    def classify_clarification(original_query, last_question, answer):
        classifier_calls.append((original_query, last_question, answer))
        return IntentRecognitionResult(
            intent="today_workout_recommendation",
            confidence=0.9,
            source="llm",
            candidates=[
                IntentCandidate(intent="today_workout_recommendation", confidence=0.9)
            ],
        )

    def fake_recommendation(self, *, user_query, **kwargs):
        captured_queries.append(user_query)
        yield {
            "kind": "result",
            "result": TodayWorkoutRecommendationResult(True, "recommended", "ok"),
        }

    service.intent_classifier.classify_clarification = classify_clarification
    monkeypatch.setattr(
        "fitmind_agent.services.chat_service.TodayWorkoutRecommendationService.stream_maybe_handle",
        fake_recommendation,
    )
    response = service.handle(
        ChatRequest(user_id=user.id, thread_id=chat.thread_id, message="补充", persist_log=True)
    )

    assert classifier_calls == [(record.original_query, record.last_question, "补充")]
    assert captured_queries == ["原始\n补充"]
    assert response.clarification and response.clarification["status"] == "resolved"
    latest_user_log = (
        db.query(ConversationLog)
        .filter_by(role="user")
        .order_by(ConversationLog.id.desc())
        .first()
    )
    assert latest_user_log.message_text == "补充"


def test_integration_failed_is_terminal_without_business_call():
    db, user, chat = setup()
    record = IntentClarificationService(db).create(
        user_id=user.id, session_id=chat.id, query="原始", result=unknown()
    )
    record.attempt_count = 2
    db.commit()
    service = ChatService(db=db, llm_service=FakeLLM())
    service.intent_classifier.classify = lambda *a, **k: unknown()
    service.intent_classifier.classify_clarification = lambda *a: unknown()
    assert (
        events(
            service,
            ChatRequest(
                user_id=user.id, thread_id=chat.thread_id, message="不清楚", persist_log=True
            ),
        )[-1]["workflow"]["action"]
        == "failed"
    )


def test_integration_pending_draft_precedes_clarification():
    db, user, chat = setup()
    WorkoutRecordDraftRepository(db).create(
        {
            "user_id": user.id,
            "session_id": chat.id,
            "status": "pending",
            "raw_text": "待确认训练草稿",
            "draft_payload": {"exercises": []},
        }
    )
    service = ChatService(db=db)
    service.intent_classifier.classify = lambda *a, **k: IntentRecognitionResult(
        intent="today_nutrition_record",
        confidence=0.95,
        source="llm",
        candidates=[IntentCandidate(intent="today_nutrition_record", confidence=0.95)],
    )

    result = events(
        service,
        ChatRequest(
            user_id=user.id,
            thread_id=chat.thread_id,
            message="今天吃了两个鸡蛋",
            persist_log=True,
        ),
    )

    assert result[-1]["workflow"]["action"] == "pending_conflict"
    assert db.query(IntentClarification).count() == 0


def test_integration_resolved_persists_final_intent_log():
    db, user, chat = setup()
    record = IntentClarificationService(db).create(
        user_id=user.id,
        session_id=chat.id,
        query="原始",
        result=IntentRecognitionResult(intent="general_chat", confidence=0.1, source="fallback"),
    )
    service = ChatService(db=db, llm_service=FakeLLM())
    service.intent_classifier.classify = lambda *a, **k: unknown()
    service.handle(
        ChatRequest(
            user_id=user.id,
            thread_id=chat.thread_id,
            message="选",
            persist_log=True,
            clarification=ClarificationInput(
                id=record.id, action="select", selected_intent="general_chat"
            ),
        )
    )
    from fitmind_agent.db.models import IntentRecognitionLog

    assert db.query(IntentRecognitionLog).filter_by(final_intent="general_chat").count() >= 1


def test_integration_classifier_receives_only_latest_four_context_logs():
    db, user, chat = setup()
    log_repo = ConversationLogRepository(db)
    for index in range(6):
        log_repo.create(
            user_id=user.id,
            thread_id=chat.thread_id,
            session_id=chat.id,
            role="user" if index % 2 == 0 else "assistant",
            message_text=f"context-message-{index}",
        )

    service = ChatService(db=db)
    captured = []
    service.intent_classifier.classify = lambda query, context="": (
        captured.append((query, context)) or unknown()
    )
    service._classify_with_workflow_context(
        ChatRequest(user_id=user.id, thread_id=chat.thread_id, message="当前"), chat.id
    )
    query, context = captured[0]
    assert query == "当前"
    assert "context-message-0" not in context
    assert "context-message-1" not in context
    for index in range(2, 6):
        assert f"context-message-{index}" in context
