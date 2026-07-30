from datetime import date
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fitmind_agent.api.app import create_app
from fitmind_agent.db.models import Base
from fitmind_agent.db.models import User
from fitmind_agent.db.session import get_db_session
from fitmind_agent.repositories.workout import WorkoutRecordRepository
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.services.intent_router import IntentRouter
from fitmind_agent.services.workout_history_service import WorkoutHistoryService


class ScriptedHistoryLLM:
    def __init__(self, response: str) -> None:
        self.response = response

    def generate_text(self, **kwargs: str) -> str:
        assert "训练历史查询条件" in kwargs["user_text"]
        return self.response


def build_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    app = create_app()

    def override_get_db_session() -> Session:
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app), session


def seed_training_history(session: Session) -> int:
    user = User(email="history@example.com", username="history_user", password_hash="hash")
    session.add(user)
    session.commit()
    session.refresh(user)

    repo = WorkoutRecordRepository(session)
    chest = repo.create_record(
        user_id=user.id,
        record_date=date.today() - timedelta(days=1),
        session_name="胸部训练",
        raw_text="卧推和划船",
        duration_minutes=55,
        perceived_exertion=7,
    )
    repo.replace_items(
        workout_record_id=chest.id,
        items=[
            {
                "exercise_name": "杠铃卧推",
                "exercise_type": "strength",
                "sets_count": 4,
                "reps_text": "8次",
                "weight_text": "60kg",
            },
            {
                "exercise_name": "坐姿划船",
                "exercise_type": "strength",
                "sets_count": 3,
                "reps_text": "10次",
                "weight_text": "50kg",
            },
        ],
    )
    cardio = repo.create_record(
        user_id=user.id,
        record_date=date.today() - timedelta(days=3),
        session_name="晨间跑步",
        raw_text="轻松慢跑",
        duration_minutes=30,
        completion_status="partial",
    )
    repo.replace_items(
        workout_record_id=cardio.id,
        items=[
            {
                "exercise_name": "慢跑",
                "exercise_type": "cardio",
                "duration_text": "30分钟",
                "distance_text": "4公里",
            }
        ],
    )
    unknown = repo.create_record(
        user_id=user.id,
        record_date=date.today() - timedelta(days=4),
        session_name="功能训练",
        raw_text="雪橇推行",
    )
    repo.replace_items(
        workout_record_id=unknown.id,
        items=[
            {"exercise_name": "雪橇推行", "exercise_type": "other", "sets_count": 5},
        ],
    )
    return user.id


def test_workout_history_route_is_ready() -> None:
    route = IntentRouter().route(
        IntentRecognitionResult(
            intent="workout_history_query",
            confidence=0.94,
            source="llm",
            reason="用户查询历史训练。",
        )
    )

    assert route.status == "ready"
    assert route.module_name == "workout_history_query_service"


def test_history_api_filters_by_muscle_and_exercise() -> None:
    client, session = build_client()
    user_id = seed_training_history(session)
    today = date.today().isoformat()
    start_date = (date.today() - timedelta(days=6)).isoformat()

    chest_response = client.get(
        "/api/v1/workouts/history",
        params={
            "user_id": user_id,
            "start_date": start_date,
            "end_date": today,
            "muscle_group": "chest",
        },
    )
    assert chest_response.status_code == 200
    chest_payload = chest_response.json()
    assert chest_payload["summary"]["record_count"] == 1
    assert chest_payload["records"][0]["items"][0]["exercise_name"] == "杠铃卧推"

    exercise_response = client.get(
        "/api/v1/workouts/history",
        params={
            "user_id": user_id,
            "start_date": start_date,
            "end_date": today,
            "exercise_keyword": "划船",
        },
    )
    assert exercise_response.status_code == 200
    exercise_payload = exercise_response.json()
    assert exercise_payload["summary"]["record_count"] == 1
    assert [item["exercise_name"] for item in exercise_payload["records"][0]["items"]] == ["坐姿划船"]

    other_response = client.get(
        "/api/v1/workouts/history",
        params={
            "user_id": user_id,
            "start_date": start_date,
            "end_date": today,
            "muscle_group": "other",
        },
    )
    assert other_response.status_code == 200
    assert other_response.json()["records"][0]["items"][0]["exercise_name"] == "雪橇推行"

    paged_response = client.get(
        "/api/v1/workouts/history",
        params={
            "user_id": user_id,
            "start_date": start_date,
            "end_date": today,
            "page": 2,
            "page_size": 1,
        },
    )
    assert paged_response.status_code == 200
    assert paged_response.json()["pagination"] == {
        "page": 2,
        "page_size": 1,
        "total_records": 3,
        "total_pages": 3,
    }

    empty_response = client.get(
        "/api/v1/workouts/history",
        params={
            "user_id": user_id,
            "start_date": start_date,
            "end_date": today,
            "exercise_keyword": "不存在的动作",
        },
    )
    assert empty_response.status_code == 200
    assert empty_response.json()["records"] == []


def test_history_api_rejects_ranges_over_ninety_days() -> None:
    client, session = build_client()
    user_id = seed_training_history(session)

    response = client.get(
        "/api/v1/workouts/history",
        params={
            "user_id": user_id,
            "start_date": (date.today() - timedelta(days=90)).isoformat(),
            "end_date": date.today().isoformat(),
        },
    )

    assert response.status_code == 422
    assert "90" in response.json()["detail"]


def test_history_service_streams_filters_records_and_markdown() -> None:
    _, session = build_client()
    user_id = seed_training_history(session)
    service = WorkoutHistoryService(
        llm_service=ScriptedHistoryLLM(
            '{"start_date": null, "end_date": null, "muscle_group": "chest", "exercise_keyword": "卧推"}'
        )
    )

    events = list(
        service.stream_maybe_handle(
            user_id=user_id,
            user_query="查一下最近的胸部卧推记录",
            intent_result=IntentRecognitionResult(
                intent="workout_history_query",
                confidence=0.95,
                source="llm",
                reason="用户查询胸部卧推历史。",
            ),
            db=session,
        )
    )

    nodes = {event["event"]["node"] for event in events if event["kind"] == "progress"}
    assert {
        "history_query_start",
        "parse_history_filters",
        "query_workout_records",
        "filter_by_muscle_group",
        "history_complete",
    } <= nodes
    result = events[-1]["result"]
    assert result.handled is True
    assert "## 查询范围" in result.reply
    assert "杠铃卧推" in result.reply
    assert result.payload["summary"]["strength_sets_count"] == 4
