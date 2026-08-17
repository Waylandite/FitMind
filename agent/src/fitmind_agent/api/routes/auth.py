from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import status
from sqlalchemy.orm import Session

from fitmind_agent.api.dependencies import CurrentUser
from fitmind_agent.core.config import Settings
from fitmind_agent.core.config import get_settings
from fitmind_agent.db.session import get_db_session
from fitmind_agent.schemas.auth import AuthTokenResponse
from fitmind_agent.schemas.auth import AuthUserRead
from fitmind_agent.schemas.auth import ChangePasswordRequest
from fitmind_agent.schemas.auth import LoginRequest
from fitmind_agent.schemas.auth import RegisterRequest
from fitmind_agent.services.auth_service import AuthenticationError
from fitmind_agent.services.auth_service import AuthConflictError
from fitmind_agent.services.auth_service import AuthService
from fitmind_agent.services.auth_service import IssuedAuthTokens


router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", maxsplit=1)[0].strip()
    return request.client.host if request.client else None


def _set_refresh_cookie(
    response: Response,
    refresh_token: str,
    settings: Settings,
) -> None:
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=refresh_token,
        max_age=settings.auth_refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path=f"{settings.api_prefix}/auth",
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path=f"{settings.api_prefix}/auth",
    )


def _token_response(tokens: IssuedAuthTokens) -> AuthTokenResponse:
    return AuthTokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=AuthUserRead.model_validate(tokens.user),
    )


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthTokenResponse:
    try:
        tokens = AuthService(db, settings).register(
            payload,
            user_agent=request.headers.get("user-agent"),
            ip_address=_client_ip(request),
        )
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    _set_refresh_cookie(response, tokens.refresh_token, settings)
    return _token_response(tokens)


@router.post("/login", response_model=AuthTokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthTokenResponse:
    try:
        tokens = AuthService(db, settings).login(
            payload,
            user_agent=request.headers.get("user-agent"),
            ip_address=_client_ip(request),
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    _set_refresh_cookie(response, tokens.refresh_token, settings)
    return _token_response(tokens)


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthTokenResponse:
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if not refresh_token:
        _clear_refresh_cookie(response, settings)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态无效或已过期")
    try:
        tokens = AuthService(db, settings).refresh(
            refresh_token,
            user_agent=request.headers.get("user-agent"),
            ip_address=_client_ip(request),
        )
    except AuthenticationError as exc:
        _clear_refresh_cookie(response, settings)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    _set_refresh_cookie(response, tokens.refresh_token, settings)
    return _token_response(tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    current_user: CurrentUser,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> None:
    AuthService(db, settings).logout(
        request.cookies.get(settings.auth_refresh_cookie_name),
        user_id=current_user.id,
    )
    _clear_refresh_cookie(response, settings)


@router.get("/me", response_model=AuthUserRead)
def me(current_user: CurrentUser) -> AuthUserRead:
    return AuthUserRead.model_validate(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    current_user: CurrentUser,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> None:
    try:
        AuthService(db, settings).change_password(
            current_user,
            payload.current_password,
            payload.new_password,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    _clear_refresh_cookie(response, settings)
