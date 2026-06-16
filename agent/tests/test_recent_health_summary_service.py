from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fitmind_agent.db.models import Base
from fitmind_agent.db.models import User
from fitmind_agent.repositories.nutrition import BodyStatusRecordRepository
from fitmind_agent.repositories.nutrition import NutritionRecordRepository
from fitmind_agent.repositories.workout import WorkoutPlanRepository
from fitmind_agent.repositories.workout import WorkoutRecordRepository
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.services import recent_health_summary_service
from fitmind_agent.services.intent_router import IntentRouter
from fitmind_agent.services.recent_health_summary_service import RecentHealthSummaryService


class ScriptedLLMService:
    def generate_text(self, **kwargs) -> str:
        assert "最近 7 天训练记录" in kwargs["user_text"]
        assert "最近 7 天饮食记录" in kwargs["user_text"]
        assert "最近 7 天身体状态记录" in kwargs["user_text"]
        assert "用户最新一次训练计划" in kwargs["user_text"]
        return (
            "## 最近 7 天总结\n整体记录稳定。\n\n"
            "### 身体状态\n- 睡眠和疲劳已有记录。\n\n"
            "### 饮食状态\n- 蛋白和热量已有累计。\n\n"
            "### 训练状态\n- 有训练记录。\n\n"
            "### 需要注意\n- 继续补充记录。\n\n"
            "### 下一步建议\n- 保持记录。"
        )


def test_recent_health_summary_route_is_ready() -> None:
    result = IntentRouter().route(
        IntentRecognitionResult(
            intent="recent_health_summary",
            confidence=0.92,
            source="llm",
            reason="用户要求总结最近状态。",
        )
    )

    assert result.status == "ready"
    assert result.module_name == "health_summary_agent"


def test_recent_health_summary_streams_query_progress_and_reply(monkeypatch, tmp_path) -> None:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'summary.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    test_session_local = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(recent_health_summary_service, "SessionLocal", test_session_local)

    today = date.today()
    with test_session_local() as session:
        user = User(email="summary@example.com", username="summary_user", password_hash="hash")
        session.add(user)
        session.commit()
        session.refresh(user)

        workout_repo = WorkoutRecordRepository(session)
        workout = workout_repo.create_record(
            user_id=user.id,
            record_date=today,
            session_name="胸部训练",
            raw_text="卧推 4 组",
            perceived_exertion=7,
        )
        workout_repo.replace_items(
            workout_record_id=workout.id,
            items=[
                {
                    "exercise_name": "卧推",
                    "exercise_type": "strength",
                    "sets_count": 4,
                    "reps_text": "8次",
                    "weight_text": "60kg",
                }
            ],
        )
        NutritionRecordRepository(session).upsert_daily_record(
            user_id=user.id,
            record_date=today,
            raw_text="早餐鸡蛋牛奶",
            calories_estimate=Decimal("420"),
            protein_g_estimate=Decimal("32"),
        )
        BodyStatusRecordRepository(session).upsert_daily_record(
            user_id=user.id,
            record_date=today,
            raw_text="睡了7小时，精神不错",
            sleep_hours=Decimal("7"),
            fatigue_level=3,
        )
        WorkoutPlanRepository(session).create_plan(
            user_id=user.id,
            title="增肌计划",
            plan_date=today,
            raw_text="练三休一，胸背腿循环",
        )
        user_id = user.id

    service = RecentHealthSummaryService(llm_service=ScriptedLLMService())
    events = list(
        service.stream_maybe_handle(
            user_id=user_id,
            user_query="总结一下我最近一周训练、饮食和身体状态",
            intent_result=IntentRecognitionResult(
                intent="recent_health_summary",
                confidence=0.93,
                source="llm",
                reason="用户要求总结最近状态。",
            ),
        )
    )

    progress_events = [event["event"] for event in events if event["kind"] == "progress"]
    titles = [event["title"] for event in progress_events]

    assert any("训练数据" in title for title in titles)
    assert any("饮食数据" in title for title in titles)
    assert any("身体状态数据" in title for title in titles)
    assert any("最新训练计划" in title for title in titles)
    assert events[-1]["kind"] == "result"
    assert events[-1]["result"].handled is True
    assert "## 最近 7 天总结" in events[-1]["result"].reply
    assert events[-1]["result"].payload["workout_records"][0]["items"][0]["exercise_type"] == "strength"
    assert events[-1]["result"].payload["latest_workout_plan"]["title"] == "增肌计划"
