from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.orm import Session

from fitmind_agent.db.models import AuthRefreshSession
from fitmind_agent.db.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email).limit(1))

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username).limit(1))

    def get_by_identifier(self, identifier: str) -> User | None:
        normalized = identifier.strip()
        return self.session.scalar(
            select(User)
            .where(
                or_(
                    User.email == normalized.lower(),
                    User.username == normalized,
                )
            )
            .limit(1)
        )

    def create(self, data: Mapping[str, Any]) -> User:
        user = User(**dict(data))
        self.session.add(user)
        self.session.flush()
        return user


class RefreshSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: Mapping[str, Any]) -> AuthRefreshSession:
        record = AuthRefreshSession(**dict(data))
        self.session.add(record)
        self.session.flush()
        return record

    def get_by_hash_for_update(self, token_hash: str) -> AuthRefreshSession | None:
        stmt = (
            select(AuthRefreshSession)
            .where(AuthRefreshSession.token_hash == token_hash)
            .with_for_update()
            .limit(1)
        )
        return self.session.scalar(stmt)

    def revoke_family(self, family_id: str, revoked_at: datetime) -> None:
        records = self.session.scalars(
            select(AuthRefreshSession).where(
                AuthRefreshSession.family_id == family_id,
                AuthRefreshSession.revoked_at.is_(None),
            )
        )
        for record in records:
            record.revoked_at = revoked_at

    def revoke_all_for_user(self, user_id: int, revoked_at: datetime) -> None:
        records = self.session.scalars(
            select(AuthRefreshSession).where(
                AuthRefreshSession.user_id == user_id,
                AuthRefreshSession.revoked_at.is_(None),
            )
        )
        for record in records:
            record.revoked_at = revoked_at
