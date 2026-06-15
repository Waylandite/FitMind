from time import perf_counter

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from fitmind_agent.db.models import Base
from fitmind_agent.db.models import ChatTurnTokenUsage
from fitmind_agent.db.models import LLMCallLog
from fitmind_agent.services import token_usage_tracker
from fitmind_agent.services.token_usage_tracker import TokenUsageContext
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker


def test_token_usage_tracker_writes_call_logs_and_turn_aggregate(monkeypatch, tmp_path) -> None:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'token_usage.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    test_session_local = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(token_usage_tracker, "SessionLocal", test_session_local)

    request_id = "token-test-request"
    with TokenUsageTracker.context(
        TokenUsageContext(
            request_id=request_id,
            user_id=None,
            thread_id="thread-token-test",
            session_id=None,
            workflow="intent",
            node_name="intent_classifier",
        )
    ):
        TokenUsageTracker.record_call(
            provider="deepseek",
            model="deepseek-v4-flash",
            is_stream=False,
            started_at=perf_counter(),
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
            },
        )
        with TokenUsageTracker.scoped(workflow="nutrition_record", node_name="nutrition_react_decide"):
            TokenUsageTracker.record_call(
                provider="deepseek",
                model="deepseek-v4-flash",
                is_stream=False,
                started_at=perf_counter(),
                usage={
                    "prompt_tokens": 200,
                    "completion_tokens": 50,
                    "total_tokens": 250,
                },
            )

    TokenUsageTracker.flush_for_tests()
    TokenUsageTracker.aggregate_turn(
        request_id=request_id,
        user_id=None,
        thread_id="thread-token-test",
        session_id=None,
        intent_type="today_nutrition_record",
    )
    TokenUsageTracker.flush_for_tests()

    with test_session_local() as session:
        calls = list(session.scalars(select(LLMCallLog)))
        aggregate = session.scalar(select(ChatTurnTokenUsage).where(ChatTurnTokenUsage.request_id == request_id))

    assert len(calls) == 2
    calls_by_workflow = {call.workflow: call for call in calls}
    assert calls_by_workflow["intent"].prompt_tokens == 100
    assert calls_by_workflow["nutrition_record"].completion_tokens == 50
    assert aggregate is not None
    assert aggregate.llm_call_count == 2
    assert aggregate.total_prompt_tokens == 300
    assert aggregate.total_completion_tokens == 70
    assert aggregate.total_tokens == 370
    assert aggregate.model_breakdown["deepseek-v4-flash"]["call_count"] == 2
