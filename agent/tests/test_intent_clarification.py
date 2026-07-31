from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy import BigInteger
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fitmind_agent.db.models import Base, ChatSession, User
from fitmind_agent.schemas.intent import IntentCandidate, IntentRecognitionResult
from fitmind_agent.services.intent_clarification_service import IntentClarificationService
from fitmind_agent.services.intent_resolution_policy import IntentResolutionPolicy


def build_session() -> tuple[Session, User, ChatSession]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(email="clarify@example.com", username="clarify", password_hash="hash")
    db.add(user)
    db.commit()
    chat_session = ChatSession(user_id=user.id, thread_id="clarify-thread", title="澄清测试")
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return db, user, chat_session


def result(intent: str, confidence: float, candidates: list[tuple[str, float]] | None = None):
    return IntentRecognitionResult(
        intent=intent,
        confidence=confidence,
        source="llm",
        candidates=[IntentCandidate(intent=name, confidence=score) for name, score in (candidates or [(intent, confidence)])],
    )


def test_policy_requires_ambiguous_and_allows_high_confidence() -> None:
    policy = IntentResolutionPolicy()
    assert not policy.needs_clarification(result("today_workout_record", 0.9))
    assert policy.needs_clarification(result("today_workout_record", 0.77))
    assert policy.needs_clarification(result("today_workout_record", 0.9, [("today_workout_record", 0.9), ("today_nutrition_record", 0.8)]))
    assert policy.needs_clarification(result("unknown", 1.0))


def test_policy_rejects_mismatched_top_candidate() -> None:
    assert IntentResolutionPolicy().needs_clarification(
        result("today_workout_record", 0.9, [("today_nutrition_record", 0.95)])
    )


def test_clarification_prompt_is_rendered_and_parsed() -> None:
    from fitmind_agent.services.intent_classifier import IntentClassifier

    class FakeLLM:
        def generate_text(self, **kwargs):
            assert "原始需求：记录一下" in kwargs["user_text"]
            assert "用户补充：饮食" in kwargs["user_text"]
            return '{"intent":"today_nutrition_record","confidence":0.9,"candidates":[{"intent":"today_nutrition_record","confidence":0.9}]}'

    parsed = IntentClassifier(llm_service=FakeLLM()).classify_clarification("记录一下", "记录什么？", "饮食")
    assert parsed.intent == "today_nutrition_record"


def test_active_event_has_restore_protocol() -> None:
    db, user, chat_session = build_session()
    record = IntentClarificationService(db).create(user_id=user.id, session_id=chat_session.id, query="记录", result=result("unknown", 0.1))
    event = IntentClarificationService.event(record)
    assert event["type"] == "clarification"
    assert event["clarification_id"] == record.id
    assert event["options"] and event["attempt"] == 1


def test_chat_service_is_instantiable_for_clarification_flow() -> None:
    from fitmind_agent.services.chat_service import ChatService
    db, _, _ = build_session()
    assert ChatService(db=db).intent_policy is not None


def test_stream_sse_requested_event_shape() -> None:
    import json
    from fitmind_agent.services.chat_service import ChatService
    from fitmind_agent.schemas.chat import ChatRequest

    db, user, session = build_session()
    service = ChatService(db=db)
    service.intent_classifier.classify = lambda *args, **kwargs: result("unknown", 0.1)  # type: ignore[method-assign]
    events = [json.loads(item[6:]) for item in service.stream_handle(ChatRequest(user_id=user.id, thread_id=session.thread_id, message="帮我记录", persist_log=True)) if item.startswith("data: ")]
    assert any(item["type"] == "clarification" and item["action"] == "requested" for item in events)
    assert events[-1]["workflow"]["action"] == "awaiting_user"


def test_stream_terminal_cancel_done_action() -> None:
    import json
    from fitmind_agent.services.chat_service import ChatService
    from fitmind_agent.schemas.chat import ChatRequest, ClarificationInput

    db, user, session = build_session()
    record = IntentClarificationService(db).create(user_id=user.id, session_id=session.id, query="记录", result=result("unknown", 0.1))
    events = [json.loads(item[6:]) for item in ChatService(db=db).stream_handle(ChatRequest(user_id=user.id, thread_id=session.thread_id, message="取消", persist_log=True, clarification=ClarificationInput(id=record.id, action="cancel"))) if item.startswith("data: ")]
    assert events[-1]["workflow"]["action"] == "cancelled"


def test_repository_active_key_clears_on_cancel() -> None:
    db, user, session = build_session()
    service = IntentClarificationService(db)
    record = service.create(user_id=user.id, session_id=session.id, query="记录", result=result("unknown", 0.1))
    assert record.active_session_key == session.id
    assert service.cancel(clarification_id=record.id, user_id=user.id, session_id=session.id).active_session_key is None


def test_cross_user_selection_does_not_resolve() -> None:
    db, user, session = build_session()
    record = IntentClarificationService(db).create(user_id=user.id, session_id=session.id, query="记录", result=result("unknown", 0.1))
    assert IntentClarificationService(db).select(clarification_id=record.id, user_id=user.id + 99, session_id=session.id, intent="today_workout_record") is None


def test_event_contains_terminal_status_after_failure() -> None:
    db, user, session = build_session()
    service = IntentClarificationService(db)
    record = service.create(user_id=user.id, session_id=session.id, query="记录", result=result("unknown", 0.1))
    record = service.retry(record, result("unknown", 0.1), "不知道")
    record = service.retry(record, result("unknown", 0.1), "还是不知道")
    assert IntentClarificationService.event(record, "failed")["status"] == "failed"


def test_contextual_classification_accepts_context_argument() -> None:
    from fitmind_agent.services.intent_classifier import IntentClassifier
    assert IntentClassifier().classify_by_keywords("继续记录这个") is None


def test_sync_response_schema_accepts_clarification() -> None:
    from fitmind_agent.schemas.chat import ChatResponse
    assert ChatResponse(user_id=1, thread_id="x", intent="unknown", reply="x", clarification={"status": "pending"}).clarification["status"] == "pending"


def test_button_selection_is_owned_candidate_only_and_resolves() -> None:
    db, user, chat_session = build_session()
    service = IntentClarificationService(db)
    record = service.create(user_id=user.id, session_id=chat_session.id, query="帮我记一下", result=result("unknown", 0.1))
    assert service.select(clarification_id=record.id, user_id=user.id + 1, session_id=chat_session.id, intent="today_workout_record") is None
    assert service.select(clarification_id=record.id, user_id=user.id, session_id=chat_session.id, intent="general_chat") is None
    resolved = service.select(clarification_id=record.id, user_id=user.id, session_id=chat_session.id, intent="today_workout_record")
    assert resolved is not None and resolved.status == "resolved"
    assert resolved.resolution_source == "button"


def test_second_failed_reply_and_expiry_are_safe() -> None:
    db, user, chat_session = build_session()
    service = IntentClarificationService(db)
    record = service.create(user_id=user.id, session_id=chat_session.id, query="记录一下", result=result("unknown", 0.1))
    asked_again = service.retry(record, result("unknown", 0.1), "都可以")
    assert asked_again.status == "pending" and asked_again.attempt_count == 2
    failed = service.retry(asked_again, result("unknown", 0.1), "不知道")
    assert failed.status == "failed" and failed.resolved_intent is None

    expired = service.create(user_id=user.id, session_id=chat_session.id, query="再来", result=result("unknown", 0.1))
    expired.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert service.select(clarification_id=expired.id, user_id=user.id, session_id=chat_session.id, intent="today_workout_record") is None
    assert expired.status == "expired"


def test_create_supersedes_previous_pending_record() -> None:
    db, user, chat_session = build_session()
    service = IntentClarificationService(db)
    first = service.create(user_id=user.id, session_id=chat_session.id, query="记录", result=result("unknown", 0.1))
    second = service.create(user_id=user.id, session_id=chat_session.id, query="帮忙", result=result("unknown", 0.1))
    db.refresh(first)
    assert first.status == "superseded"
    assert second.status == "pending"


def test_intent_clarification_identifiers_are_bigint() -> None:
    from fitmind_agent.db.models import IntentClarification

    table = IntentClarification.__table__
    for column_name in ("id", "user_id", "session_id", "active_session_key"):
        assert isinstance(table.c[column_name].type, BigInteger)


def test_migration_downgrade_drops_table_without_pre_dropping_fk_index() -> None:
    from pathlib import Path

    migration = Path(__file__).parents[1] / "alembic/versions/20260731_000010_add_intent_clarifications.py"
    source = migration.read_text(encoding="utf-8")
    downgrade = source.split("def downgrade()", maxsplit=1)[1]
    assert 'op.drop_table("intent_clarifications")' in downgrade
    assert "op.drop_index" not in downgrade
