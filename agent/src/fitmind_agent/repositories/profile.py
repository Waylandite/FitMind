from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from fitmind_agent.db.models import UserProfile


class UserProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_user_id(self, user_id: int) -> UserProfile | None:
        stmt = select(UserProfile).where(UserProfile.user_id == user_id).limit(1)
        return self.session.scalar(stmt)

    def create(self, data: Mapping[str, Any]) -> UserProfile:
        profile = UserProfile(**dict(data))
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)
        return profile

    def update(self, profile: UserProfile, data: Mapping[str, Any]) -> UserProfile:
        for key, value in data.items():
            setattr(profile, key, value)
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)
        return profile

    def upsert(self, user_id: int, data: Mapping[str, Any]) -> UserProfile:
        profile = self.get_by_user_id(user_id)
        payload = {"user_id": user_id, **dict(data)}
        if profile is None:
            return self.create(payload)
        payload.pop("user_id", None)
        return self.update(profile, payload)
