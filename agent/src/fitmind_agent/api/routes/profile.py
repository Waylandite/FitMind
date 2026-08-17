from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from fitmind_agent.api.dependencies import CurrentUser
from fitmind_agent.db.session import get_db_session
from fitmind_agent.schemas.profile import UserProfileRead
from fitmind_agent.schemas.profile import UserProfileUpsert
from fitmind_agent.services.profile_service import ProfileService

router = APIRouter(prefix="/profiles", tags=["profile"])


@router.get("/me", response_model=UserProfileRead | None)
def get_user_profile(
    current_user: CurrentUser, db: Session = Depends(get_db_session)
) -> UserProfileRead | None:
    return ProfileService(db).get_user_profile(current_user.id)


@router.put("/me", response_model=UserProfileRead)
def upsert_user_profile(
    payload: UserProfileUpsert,
    current_user: CurrentUser,
    db: Session = Depends(get_db_session),
) -> UserProfileRead:
    return ProfileService(db).upsert_user_profile(current_user.id, payload)
