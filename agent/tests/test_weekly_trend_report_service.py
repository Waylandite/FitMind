import json
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from fitmind_agent.db.models import Base
from fitmind_agent.db.models import ConversationLog
from fitmind_agent.db.models import IntentRecognitionLog
from fitmind_agent.db.models import User
from fitmind_agent.schemas.chat import ChatRequest
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.services import weekly_analytics_service
from fitmind_agent.services.chat_service import ChatService
from fitmind_agent.services.intent_classifier import IntentClassifier
from fitmind_agent.services.intent_router import IntentRouter
from fitmind_agent.services.weekly_analytics_service import WeeklyAnalyticsService
from fitmind_agent.services.weekly_trend_report_service import WeeklyTrendReportService


class ScriptedLLMService:
    def __init__(self) -> None:
        self.user_text = ""

    def generate_text(self, **kwargs) -> str:
        self.user_text = kwargs["user_text"]
        if "意图识别器" in kwargs["system_prompt"]:
            return json.dumps(
                {
                    "intent": "weekly_trend_report",
                    "confidence": 0.96,
                    "reason": "用户要求生成本周周报。",
                },
                ensure_ascii=False,
            )
        return (
            "## 本周结论\n记录稳定。\n\n"
            "## 与上周相比\n- 训练数据持平。\n\n"
            "## 训练表现\n- 已读取真实记录。\n\n"
            "## 饮食表现\n- 覆盖率有限。\n\n"
            "## 恢复状态\n- 暂无足够数据。\n\n"
            "## 下周行动\n- 继续记录。"
        )


class StubAnalyticsService:
    def __init__(self) -> None:
        period = WeeklyAnalyticsService().build_period(
            anchor_date=date(2026, 7, 15),
            today=date(2026, 7, 30),
        )
        self.response = WeeklyAnalyticsService()._build_response(
            period=period,
            datasets={"workouts": [], "nutrition": [], "body_status": []},
        )

    def stream_analyze(self, **kwargs):
        assert kwargs["user_id"] == 1
        yield {"kind": "dataset", "dataset": "workouts", "count": 0}
        yield {"kind": "dataset", "dataset": "nutrition", "count": 0}
        yield {"kind": "dataset", "dataset": "body_status", "count": 0}
        yield {"kind": "result", "result": self.response}


def test_weekly_trend_route_is_ready() -> None:
    result = IntentRouter().route(
        IntentRecognitionResult(
            intent="weekly_trend_report",
            confidence=0.94,
            source="llm",
            reason="用户要求生成周报。",
        )
    )

    assert result.status == "ready"
    assert result.module_name == "weekly_trend_report_service"


def test_weekly_keywords_do_not_capture_recent_recovery_query() -> None:
    classifier = IntentClassifier()

    weekly = classifier.classify_by_keywords("生成本周周报，和上周比有进步吗")
    recent = classifier.classify_by_keywords("分析一下最近恢复情况")

    assert weekly is not None
    assert weekly.intent == "weekly_trend_report"
    assert recent is not None
    assert recent.intent == "recent_health_summary"


def test_weekly_report_streams_all_progress_nodes_and_uses_analytics_payload() -> None:
    llm = ScriptedLLMService()
    service = WeeklyTrendReportService(
        llm_service=llm,
        analytics_service=StubAnalyticsService(),
    )

    events = list(
        service.stream_maybe_handle(
            user_id=1,
            user_query="生成我的本周周报",
            intent_result=IntentRecognitionResult(
                intent="weekly_trend_report",
                confidence=0.95,
                source="llm",
                reason="用户要求周报。",
            ),
        )
    )

    nodes = [
        event["event"]["node"]
        for event in events
        if event["kind"] == "progress"
    ]
    assert nodes == [
        "weekly_report_start",
        "query_weekly_workouts",
        "query_weekly_nutrition",
        "query_weekly_body_status",
        "aggregate_weekly_metrics",
        "aggregate_weekly_metrics",
        "weekly_report_llm",
        "weekly_report_llm",
        "weekly_report_complete",
    ]
    assert '"period"' in llm.user_text
    assert '"coverage"' in llm.user_text
    assert events[-1]["result"].handled is True
    assert events[-1]["result"].action == "reported"
    assert "## 本周结论" in events[-1]["result"].reply
    assert events[-1]["result"].payload["training"]["current"]["record_count"] == 0


def test_non_weekly_intent_is_ignored() -> None:
    events = list(
        WeeklyTrendReportService(
            llm_service=ScriptedLLMService(),
            analytics_service=StubAnalyticsService(),
        ).stream_maybe_handle(
            user_id=1,
            user_query="今天练什么",
            intent_result=IntentRecognitionResult(
                intent="today_workout_recommendation",
                confidence=0.9,
                source="keyword",
                reason="用户要求训练推荐。",
            ),
        )
    )

    assert events[-1]["result"].handled is False


def test_chat_stream_persists_weekly_intent_and_conversation_logs(
    monkeypatch,
    tmp_path,
) -> None:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'weekly-chat.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    test_session_local = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(weekly_analytics_service, "SessionLocal", test_session_local)

    with test_session_local() as session:
        user = User(email="weekly-chat@example.com", username="weekly_chat", password_hash="hash")
        session.add(user)
        session.commit()
        session.refresh(user)
        service = ChatService(db=session, llm_service=ScriptedLLMService())
        monkeypatch.setattr(
            service.summary_service,
            "schedule_session_compression",
            lambda session_id: None,
        )

        events = [
            json.loads(raw_event[6:].strip())
            for raw_event in service.stream_handle(
                ChatRequest(
                    user_id=user.id,
                    thread_id="weekly-thread",
                    message="生成本周周报，和上周对比",
                    persist_log=True,
                )
            )
            if raw_event.startswith("data: ")
        ]

        done = next(event for event in events if event["type"] == "done")
        logs = list(session.scalars(select(ConversationLog).order_by(ConversationLog.id)))
        intent_logs = list(session.scalars(select(IntentRecognitionLog)))

    assert done["workflow"]["name"] == "weekly_trend_report"
    assert done["intent"] == "weekly_trend_report"
    assert [log.role for log in logs] == ["user", "assistant"]
    assert intent_logs[0].final_intent == "weekly_trend_report"
    assert intent_logs[0].module_name == "weekly_trend_report_service"
