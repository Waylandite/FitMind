from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fitmind_agent.api.app import create_app
from fitmind_agent.db.models import Base
from fitmind_agent.db.models import User
from fitmind_agent.db.session import get_db_session


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


def test_profile_route_creates_default_before_upsert() -> None:
    client, session = build_client()
    user = create_user(session)

    empty_response = client.get(f"/api/v1/profiles/{user.id}")
    assert empty_response.status_code == 200
    default_profile = empty_response.json()
    assert default_profile["user_id"] == user.id
    assert default_profile["gender"] is None

    create_response = client.put(
        f"/api/v1/profiles/{user.id}",
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
        f"/api/v1/profiles/{user.id}",
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

    create_response = client.post(
        "/api/v1/memories/user-defined",
        json={
            "user_id": user.id,
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
        json={"status": "archived", "memory_value": None, "raw_text": None},
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    active_list = client.get(f"/api/v1/memories/user-defined?user_id={user.id}&status=active")
    assert active_list.status_code == 200
    assert all(record["id"] != memory_id for record in active_list.json())


def test_user_defined_memory_list_creates_default_records() -> None:
    client, session = build_client()
    user = create_user(session)

    response = client.get(f"/api/v1/memories/user-defined?user_id={user.id}&status=active")
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

    second_response = client.get(f"/api/v1/memories/user-defined?user_id={user.id}&status=active")
    assert second_response.status_code == 200
    assert len(second_response.json()) == 11
