from datetime import date
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fitmind_agent.db.models import Base
from fitmind_agent.db.models import User
from fitmind_agent.repositories.workout import WorkoutPlanRepository
from fitmind_agent.repositories.workout import WorkoutRecordRepository
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.services import today_workout_recommendation_service
from fitmind_agent.services.intent_router import IntentRouter
from fitmind_agent.services.today_workout_recommendation_service import (
    TodayWorkoutRecommendationService,
)


class ScriptedLLMService:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def generate_text(self, **kwargs) -> str:
        self.calls += 1
        assert "latest_workout_plan" in kwargs["user_text"]
        assert "recent_workout_records" in kwargs["user_text"]
        return self.response


def test_today_workout_recommendation_route_is_ready() -> None:
    result = IntentRouter().route(
        IntentRecognitionResult(
            intent="today_workout_recommendation",
            confidence=0.94,
            source="llm",
            reason="用户想知道今天怎么练。",
        )
    )

    assert result.status == "ready"
    assert result.module_name == "workout_recommendation_agent"


def test_today_workout_recommendation_streams_progress_and_payload(monkeypatch, tmp_path) -> None:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'recommendation.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    test_session_local = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(today_workout_recommendation_service, "SessionLocal", test_session_local)

    today = date.today()
    with test_session_local() as session:
        user = User(email="recommend@example.com", username="recommend_user", password_hash="hash")
        session.add(user)
        session.commit()
        session.refresh(user)

        WorkoutPlanRepository(session).create_plan(
            user_id=user.id,
            title="上肢优先计划",
            plan_date=today,
            raw_text="上肢优先，胸背肩交替，腿部每周两练。",
        )

        workout_repo = WorkoutRecordRepository(session)
        workout = workout_repo.create_record(
            user_id=user.id,
            record_date=today - timedelta(days=1),
            session_name="背部训练",
            raw_text="划船和下拉",
            completion_status="completed",
            perceived_exertion=7,
            energy_level=7,
            mood="稳定",
        )
        workout_repo.replace_items(
            workout_record_id=workout.id,
            items=[
                {
                    "exercise_name": "坐姿划船",
                    "exercise_type": "strength",
                    "sets_count": 4,
                    "reps_text": "10次",
                    "weight_text": "50kg",
                }
            ],
        )
        workout_repo.create_record(
            user_id=user.id,
            record_date=today - timedelta(days=10),
            session_name="过期记录",
            raw_text="不在最近 7 天内",
        )
        user_id = user.id

    service = TodayWorkoutRecommendationService(
        llm_service=ScriptedLLMService(
            "## 今日建议结论\n建议练上肢。\n\n"
            "## 为什么这样安排\n最近背部训练较多。\n\n"
            "## 今日训练单\n- 训练目标：上肢推拉平衡。\n- 热身：动态肩关节活动 8 分钟。\n- 主训练：卧推、划船、肩推。\n- 补充训练/有氧：快走 15 分钟。\n- 强度建议：RPE 6-7。\n- 需要避免的点：不要冲极限重量。\n\n"
            "## 如果今天状态一般\n把主训练组数减少 1 组。\n\n"
            "## 下一步建议\n训练后回来记录实际完成情况。"
        ),
    )
    events = list(
        service.stream_maybe_handle(
            user_id=user_id,
            user_query="帮我安排今天训练",
            intent_result=IntentRecognitionResult(
                intent="today_workout_recommendation",
                confidence=0.95,
                source="llm",
                reason="用户要今天训练推荐。",
            ),
        )
    )

    progress_events = [event["event"] for event in events if event["kind"] == "progress"]
    nodes = {event["node"] for event in progress_events}
    statuses = {event["status"] for event in progress_events}

    assert {"recommendation_start", "query_latest_workout_plan", "query_recent_workout_records", "recommendation_llm"} <= nodes
    assert {"queue", "thinking", "success"} <= statuses
    assert events[-1]["kind"] == "result"
    assert events[-1]["result"].handled is True
    assert "## 今日建议结论" in events[-1]["result"].reply
    assert events[-1]["result"].payload["latest_workout_plan"]["title"] == "上肢优先计划"
    assert len(events[-1]["result"].payload["recent_workout_records"]) == 1
    assert events[-1]["result"].payload["recent_workout_records"][0]["items"][0]["exercise_name"] == "坐姿划船"


def test_today_workout_recommendation_still_works_without_plan_or_records(tmp_path, monkeypatch) -> None:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'recommendation-empty.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    test_session_local = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(today_workout_recommendation_service, "SessionLocal", test_session_local)

    with test_session_local() as session:
        user = User(email="empty@example.com", username="empty_user", password_hash="hash")
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

    service = TodayWorkoutRecommendationService(
        llm_service=ScriptedLLMService(
            "## 今日建议结论\n先做全身基础训练。\n\n"
            "## 为什么这样安排\n当前缺少长期计划和近期记录。\n\n"
            "## 今日训练单\n- 训练目标：恢复节奏并建立训练惯性。\n- 热身：徒手动态活动。\n- 主训练：深蹲、俯卧撑、划船。\n- 补充训练/有氧：轻松骑车 10 分钟。\n- 强度建议：RPE 5-6。\n- 需要避免的点：不要直接做极限重量。\n\n"
            "## 如果今天状态一般\n把每个动作减到 2 组。\n\n"
            "## 下一步建议\n训练结束后回来告诉我实际完成情况。"
        ),
    )
    events = list(
        service.stream_maybe_handle(
            user_id=user_id,
            user_query="今天练什么",
            intent_result=IntentRecognitionResult(
                intent="today_workout_recommendation",
                confidence=0.95,
                source="llm",
                reason="用户要推荐。",
            ),
        )
    )

    assert events[-1]["kind"] == "result"
    assert events[-1]["result"].handled is True
    assert events[-1]["result"].payload["latest_workout_plan"] is None
    assert events[-1]["result"].payload["recent_workout_records"] == []
    assert "## 今日建议结论" in events[-1]["result"].reply
