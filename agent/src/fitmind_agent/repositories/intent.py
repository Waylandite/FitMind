from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from fitmind_agent.db.models import IntentRecognitionLog


class IntentRecognitionLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: Mapping[str, Any]) -> IntentRecognitionLog:
        log = IntentRecognitionLog(**dict(data))
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def list_recent_by_user(self, user_id: int, limit: int = 50) -> list[IntentRecognitionLog]:
        stmt = (
            select(IntentRecognitionLog)
            .where(IntentRecognitionLog.user_id == user_id)
            .order_by(IntentRecognitionLog.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def list_by_session(self, session_id: int) -> list[IntentRecognitionLog]:
        stmt = (
            select(IntentRecognitionLog)
            .where(IntentRecognitionLog.session_id == session_id)
            .order_by(IntentRecognitionLog.id.asc())
        )
        return list(self.session.scalars(stmt))
