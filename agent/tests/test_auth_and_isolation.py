from __future__ import annotations

from datetime import date

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fitmind_agent.api.app import create_app
from fitmind_agent.api import app as app_module
from fitmind_agent.core.config import Settings
from fitmind_agent.core.config import get_settings
from fitmind_agent.db.models import Base
from fitmind_agent.db.models import User
from fitmind_agent.db.session import get_db_session
from fitmind_agent.repositories.workout import WorkoutRecordRepository


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

    def override_get_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app), session


def register(
    client: TestClient,
    *,
    email: str = "alice@example.com",
    username: str = "alice",
    password: str = "secure-pass-123",
) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert response.status_code == 201
    return response.json()


def bearer(payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


def test_non_local_environment_requires_secure_refresh_cookie(monkeypatch) -> None:
    monkeypatch.setenv("FITMIND_ENV", "production")
    monkeypatch.setenv("FITMIND_AUTH_SECRET_KEY", "a" * 64)
    monkeypatch.setenv("FITMIND_AUTH_COOKIE_SECURE", "false")
    settings = Settings(_env_file=None)
    assert settings.environment == "production"

    monkeypatch.setattr(app_module, "get_settings", lambda: settings)
    with pytest.raises(RuntimeError, match="FITMIND_AUTH_COOKIE_SECURE"):
        app_module.create_app()


def test_register_login_and_password_hash() -> None:
    client, db = build_client()
    payload = register(client, email="ALICE@Example.com")

    user = db.get(User, payload["user"]["id"])
    assert user is not None
    assert user.email == "alice@example.com"
    assert user.password_hash != "secure-pass-123"
    assert user.password_hash.startswith("$argon2")

    me = client.get("/api/v1/auth/me", headers=bearer(payload))
    assert me.status_code == 200
    assert me.json()["username"] == "alice"

    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "username": "another",
            "password": "secure-pass-456",
        },
    )
    assert duplicate.status_code == 409

    wrong = client.post(
        "/api/v1/auth/login",
        json={"identifier": "alice@example.com", "password": "wrong-password"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "账号或密码错误"

    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "alice", "password": "secure-pass-123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == user.id

    user.status = "disabled"
    db.commit()
    assert client.get("/api/v1/auth/me", headers=bearer(payload)).status_code == 401
    disabled_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "alice", "password": "secure-pass-123"},
    )
    assert disabled_login.status_code == 401
    assert disabled_login.json()["detail"] == "账号或密码错误"


def test_refresh_rotation_replay_and_cookie_security() -> None:
    client, _ = build_client()
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "username": "refresh_user",
            "password": "secure-pass-123",
        },
    )
    old_cookie = register_response.cookies.get("fitmind_refresh_token")
    assert old_cookie
    set_cookie = register_response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/api/v1/auth" in set_cookie

    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    new_cookie = refreshed.cookies.get("fitmind_refresh_token")
    assert new_cookie and new_cookie != old_cookie

    # Remove the domain-scoped current cookie before replaying the old token.
    client.cookies.clear()
    client.cookies.set("fitmind_refresh_token", old_cookie, path="/api/v1/auth")
    replay = client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401

    client.cookies.clear()
    client.cookies.set("fitmind_refresh_token", new_cookie, path="/api/v1/auth")
    revoked_family = client.post("/api/v1/auth/refresh")
    assert revoked_family.status_code == 401


def test_logout_revokes_refresh_session_and_clears_cookie() -> None:
    client, _ = build_client()
    payload = register(
        client,
        email="logout@example.com",
        username="logout_user",
    )

    response = client.post("/api/v1/auth/logout", headers=bearer(payload))

    assert response.status_code == 204
    assert "fitmind_refresh_token=\"\"" in response.headers["set-cookie"]
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_change_password_invalidates_access_and_refresh_sessions() -> None:
    client, _ = build_client()
    payload = register(
        client,
        email="password@example.com",
        username="password_user",
    )
    old_headers = bearer(payload)

    changed = client.post(
        "/api/v1/auth/change-password",
        headers=old_headers,
        json={
            "current_password": "secure-pass-123",
            "new_password": "new-secure-pass-456",
        },
    )
    assert changed.status_code == 204
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 401
    assert client.post("/api/v1/auth/refresh").status_code == 401

    old_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "password_user", "password": "secure-pass-123"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "password_user", "password": "new-secure-pass-456"},
    )
    assert new_login.status_code == 200


def test_invalid_jwt_and_unauthenticated_requests_are_rejected() -> None:
    client, _ = build_client()
    assert client.get("/api/v1/memories/sessions").status_code == 401
    stream_response = client.post(
        "/api/v1/chat/stream",
        json={"message": "今天练了深蹲", "thread_id": "unauthenticated-thread"},
    )
    assert stream_response.status_code == 401
    assert "text/event-stream" not in stream_response.headers.get("content-type", "")

    payload = register(
        client,
        email="forged@example.com",
        username="forged_user",
    )
    forged_owner = client.post(
        "/api/v1/chat/stream",
        headers=bearer(payload),
        json={
            "message": "今天练了深蹲",
            "thread_id": "forged-owner-thread",
            "user_id": 999,
        },
    )
    assert forged_owner.status_code == 422

    settings = get_settings()
    invalid_audience = jwt.encode(
        {
            "sub": "1",
            "typ": "access",
            "jti": "invalid-audience",
            "ver": 1,
            "iat": 1,
            "exp": 4_102_444_800,
            "iss": settings.auth_issuer,
            "aud": "another-app",
        },
        settings.auth_secret_key,
        algorithm="HS256",
    )
    response = client.get(
        "/api/v1/memories/sessions",
        headers={"Authorization": f"Bearer {invalid_audience}"},
    )
    assert response.status_code == 401


def test_users_cannot_access_each_others_resources() -> None:
    client, db = build_client()
    alice = register(client)
    bob = register(
        client,
        email="bob@example.com",
        username="bob",
        password="secure-pass-456",
    )
    alice_headers = bearer(alice)
    bob_headers = bearer(bob)

    session_response = client.post(
        "/api/v1/memories/sessions",
        headers=alice_headers,
        json={"thread_id": "alice-thread", "title": "Alice session"},
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["id"]
    assert (
        client.get(
            f"/api/v1/memories/sessions/{session_id}/messages", headers=bob_headers
        ).status_code
        == 404
    )

    memory_response = client.post(
        "/api/v1/memories/user-defined",
        headers=alice_headers,
        json={
            "memory_key": "response_style",
            "memory_category": "conversation_preference",
            "memory_value": "简洁",
        },
    )
    assert memory_response.status_code == 200
    memory_id = memory_response.json()["id"]
    assert (
        client.patch(
            f"/api/v1/memories/user-defined/{memory_id}",
            headers=bob_headers,
            json={"memory_value": "详细"},
        ).status_code
        == 404
    )

    WorkoutRecordRepository(db).create_record(
        user_id=alice["user"]["id"],
        record_date=date.today(),
        session_name="Alice 私有训练",
        raw_text="深蹲 5 组",
    )
    history = client.get("/api/v1/workouts/history", headers=bob_headers)
    assert history.status_code == 200
    assert history.json()["records"] == []

    bob_sessions = client.get("/api/v1/memories/sessions", headers=bob_headers)
    assert bob_sessions.status_code == 200
    assert bob_sessions.json() == []
