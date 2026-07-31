from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from fitmind_agent.db.models import IntentClarification


def _is_expired(expires_at: datetime) -> bool:
    """SQLite drops timezone metadata although production timestamps are UTC."""
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc)


class IntentClarificationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active(self, *, user_id: int, session_id: int) -> IntentClarification | None:
        record = self.session.scalar(
            select(IntentClarification)
            .where(
                IntentClarification.user_id == user_id,
                IntentClarification.session_id == session_id,
                IntentClarification.status == "pending",
            )
            .order_by(IntentClarification.id.desc())
            .limit(1)
        )
        if record is not None and _is_expired(record.expires_at):
            self.update(record, {"status": "expired"})
            return None
        return record

    def get_owned(self, *, clarification_id: int, user_id: int, session_id: int) -> IntentClarification | None:
        return self.session.scalar(
            select(IntentClarification).where(
                IntentClarification.id == clarification_id,
                IntentClarification.user_id == user_id,
                IntentClarification.session_id == session_id,
            )
        )

    def create(self, data: Mapping[str, Any]) -> IntentClarification:
        # Keep the invariant in application code as well as in the service.  This
        # also protects callers which create records directly in tests or jobs.
        user_id, session_id = int(data["user_id"]), int(data["session_id"])
        active = self.get_active(user_id=user_id, session_id=session_id)
        if active is not None:
            self.update(active, {"status": "superseded", "resolved_at": datetime.now(timezone.utc)})
        payload = dict(data)
        payload.setdefault("active_session_key", session_id)
        record = IntentClarification(**payload)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def update(self, record: IntentClarification, data: Mapping[str, Any]) -> IntentClarification:
        payload = dict(data)
        if "status" in payload:
            payload["active_session_key"] = record.session_id if payload["status"] == "pending" else None
        for key, value in payload.items():
            setattr(record, key, value)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record
