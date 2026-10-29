from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fitmind_agent.api.app import create_app
from fitmind_agent.db.models import Base
from fitmind_agent.db.models import BodyStatusRecordDraft
from fitmind_agent.db.models import ChatSession
from fitmind_agent.db.models import NutritionRecordDraft
from fitmind_agent.db.models import User
from fitmind_agent.db.models import WorkoutPlanDraft
from fitmind_agent.db.models import WorkoutRecordDraft
from fitmind_agent.db.session import get_db_session
from fitmind_agent.services.auth_service import AuthService


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


def create_user(session: Session) -> User:
    user = User(email="tester@example.com", username="tester", password_hash="hash")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def auth_headers(session: Session, user: User) -> dict[str, str]:
    token = AuthService(session).create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("draft_model", "workflow", "intent"),
    [
        (WorkoutRecordDraft, "workout_record", "today_workout_record"),
        (NutritionRecordDraft, "nutrition_record", "today_nutrition_record"),
        (BodyStatusRecordDraft, "body_status_record", "today_body_status_record"),
        (WorkoutPlanDraft, "workout_plan_update", "user_workout_plan_update"),
    ],
)
def test_pending_workflow_restores_each_draft_type(
    draft_model,
    workflow: str,
    intent: str,
) -> None:
    client, session = build_client()
    user = create_user(session)
    chat_session = ChatSession(
        user_id=user.id,
        thread_id=f"pending-{workflow}",
        session_no=1,
        title="Pending workflow",
        status="active",
    )
    session.add(chat_session)
    session.flush()
    draft = draft_model(
        user_id=user.id,
        session_id=chat_session.id,
        status="pending",
        raw_text="卧推 60kg 5 组",
        draft_payload={"raw_text": "卧推 60kg 5 组"},
    )
    session.add(draft)
    session.commit()

    response = client.get(
        f"/api/v1/memories/sessions/{chat_session.id}/pending-workflow",
        headers=auth_headers(session, user),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow"] == workflow
    assert payload["intent"] == intent
    assert payload["draft_id"] == draft.id
    assert payload["draft"]["raw_text"] == "卧推 60kg 5 组"
    assert payload["draft_actions"]["confirm_text"] == "确认保存"
    assert payload["draft_actions"]["correction_prefill"]


def test_pending_workflow_returns_null_and_hides_other_users_session() -> None:
    client, session = build_client()
    owner = create_user(session)
    other = User(email="other@example.com", username="other", password_hash="hash")
    session.add(other)
    session.flush()
    chat_session = ChatSession(
        user_id=owner.id,
        thread_id="owner-session",
        session_no=1,
        title="Owner session",
        status="active",
    )
    session.add(chat_session)
    session.commit()

    empty = client.get(
        f"/api/v1/memories/sessions/{chat_session.id}/pending-workflow",
        headers=auth_headers(session, owner),
    )
    hidden = client.get(
        f"/api/v1/memories/sessions/{chat_session.id}/pending-workflow",
        headers=auth_headers(session, other),
    )

    assert empty.status_code == 200
    assert empty.json() is None
    assert hidden.status_code == 404


def test_profile_route_creates_default_before_upsert() -> None:
    client, session = build_client()
    user = create_user(session)

    headers = auth_headers(session, user)
    empty_response = client.get("/api/v1/profiles/me", headers=headers)
    assert empty_response.status_code == 200
    default_profile = empty_response.json()
    assert default_profile["user_id"] == user.id
    assert default_profile["gender"] is None

    create_response = client.put(
        "/api/v1/profiles/me",
        headers=headers,
        json={
            "gender": "男",
            "birth_date": "1995-05-20",
            "height_cm": 176,
            "weight_kg": 71.8,
            "target_weight_kg": 68,
            "goal_type": "减脂",
            "training_level": "中级",
            "injury_notes": "左膝旧伤",
            "medical_notes": "无慢性病",
            "diet_preference": "高蛋白",
            "preferred_training_days": "周一,周三,周五",
            "remark": "晚间训练",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["user_id"] == user.id
    assert created["goal_type"] == "减脂"
    assert created["preferred_training_days"] == "周一,周三,周五"

    update_response = client.put(
        "/api/v1/profiles/me",
        headers=headers,
        json={
            "gender": "男",
            "birth_date": "1995-05-20",
            "height_cm": 178,
            "weight_kg": None,
            "target_weight_kg": 69,
            "goal_type": "增肌",
            "training_level": "高级",
            "injury_notes": None,
            "medical_notes": "体检正常",
            "diet_preference": "控糖",
            "preferred_training_days": "周二,周四",
            "remark": "晨练优先",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == created["id"]
    assert updated["goal_type"] == "增肌"
    assert updated["weight_kg"] is None
    assert updated["preferred_training_days"] == "周二,周四"

    with Session(session.get_bind()) as verify_session:
        profile = verify_session.execute(
            Base.metadata.tables["user_profiles"].select().where(
                Base.metadata.tables["user_profiles"].c.user_id == user.id
            )
        ).first()
        assert profile is not None
        assert Decimal(str(profile.height_cm)) == Decimal("178")
        assert profile.goal_type == "增肌"
        assert profile.birth_date == date(1995, 5, 20)


def test_user_defined_memory_can_be_archived_via_patch() -> None:
    client, session = build_client()
    user = create_user(session)
    headers = auth_headers(session, user)

    create_response = client.post(
        "/api/v1/memories/user-defined",
        headers=headers,
        json={
            "memory_key": "response_style",
            "memory_category": "conversation_preference",
            "memory_value": "简洁",
            "raw_text": "回答偏好：简洁",
            "priority": 100,
            "status": "active",
        },
    )
    assert create_response.status_code == 200
    memory_id = create_response.json()["id"]

    archive_response = client.patch(
        f"/api/v1/memories/user-defined/{memory_id}",
        headers=headers,
        json={"status": "archived", "memory_value": None, "raw_text": None},
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    active_list = client.get(
        "/api/v1/memories/user-defined?status=active", headers=headers
    )
    assert active_list.status_code == 200
    assert all(record["id"] != memory_id for record in active_list.json())


def test_user_defined_memory_list_creates_default_records() -> None:
    client, session = build_client()
    user = create_user(session)
    headers = auth_headers(session, user)

    response = client.get("/api/v1/memories/user-defined?status=active", headers=headers)
    assert response.status_code == 200
    records = response.json()

    assert len(records) == 11
    assert {record["memory_category"] for record in records} == {
        "fitness_preference",
        "content_preference",
        "conversation_preference",
        "diet_preference",
        "health_constraint_preference",
    }
    assert {record["memory_key"] for record in records} >= {"goal_type", "response_style", "injury_notes"}
    assert all(record["status"] == "active" for record in records)

    second_response = client.get(
        "/api/v1/memories/user-defined?status=active", headers=headers
    )
    assert second_response.status_code == 200
    assert len(second_response.json()) == 11
