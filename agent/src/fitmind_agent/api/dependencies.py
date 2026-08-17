from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from fitmind_agent.db.models import User
from fitmind_agent.db.session import get_db_session
from fitmind_agent.repositories.auth import UserRepository
from fitmind_agent.services.auth_service import AuthenticationError
from fitmind_agent.services.auth_service import AuthService


bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db_session)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()
    try:
        claims = AuthService(db).decode_access_token(credentials.credentials)
        user_id = int(claims["sub"])
    except (AuthenticationError, TypeError, ValueError, KeyError) as exc:
        raise unauthorized() from exc

    user = UserRepository(db).get_by_id(user_id)
    if (
        user is None
        or user.status != "active"
        or user.auth_version != claims.get("ver")
    ):
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
