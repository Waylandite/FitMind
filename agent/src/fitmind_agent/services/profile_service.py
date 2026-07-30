from __future__ import annotations

from sqlalchemy.orm import Session

from fitmind_agent.repositories.profile import UserProfileRepository
from fitmind_agent.schemas.profile import UserProfileRead
from fitmind_agent.schemas.profile import UserProfileUpsert


class ProfileService:
    def __init__(self, db: Session) -> None:
        self.profile_repo = UserProfileRepository(db)

    def get_user_profile(self, user_id: int) -> UserProfileRead | None:
        profile = self.profile_repo.get_by_user_id(user_id)
        if profile is None:
            profile = self.profile_repo.create({"user_id": user_id})
        return UserProfileRead.model_validate(profile)

    def upsert_user_profile(self, user_id: int, payload: UserProfileUpsert) -> UserProfileRead:
        profile = self.profile_repo.upsert(user_id, payload.model_dump())
        return UserProfileRead.model_validate(profile)
