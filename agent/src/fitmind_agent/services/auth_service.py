from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from uuid import uuid4

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fitmind_agent.core.config import Settings
from fitmind_agent.core.config import get_settings
from fitmind_agent.db.models import User
from fitmind_agent.repositories.auth import RefreshSessionRepository
from fitmind_agent.repositories.auth import UserRepository
from fitmind_agent.schemas.auth import LoginRequest
from fitmind_agent.schemas.auth import RegisterRequest


_PASSWORD_HASH = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = _PASSWORD_HASH.hash("fitmind-dummy-password")


class AuthenticationError(ValueError):
    pass


class AuthConflictError(ValueError):
    pass


@dataclass(frozen=True)
class IssuedAuthTokens:
    access_token: str
    refresh_token: str
    expires_in: int
    user: User


class AuthService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.users = UserRepository(db)
        self.refresh_sessions = RefreshSessionRepository(db)
        self.password_hash = _PASSWORD_HASH

    def register(
        self,
        payload: RegisterRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> IssuedAuthTokens:
        if self.users.get_by_email(payload.email) is not None:
            raise AuthConflictError("邮箱或用户名已被使用")
        if self.users.get_by_username(payload.username) is not None:
            raise AuthConflictError("邮箱或用户名已被使用")

        try:
            user = self.users.create(
                {
                    "email": payload.email,
                    "username": payload.username,
                    "password_hash": self.hash_password(payload.password),
                    "display_name": payload.display_name or payload.username,
                    "status": "active",
                    "auth_version": 1,
                }
            )
            tokens = self._issue_session(user, user_agent=user_agent, ip_address=ip_address)
            self.db.commit()
            self.db.refresh(user)
            return tokens
        except IntegrityError as exc:
            self.db.rollback()
            raise AuthConflictError("邮箱或用户名已被使用") from exc

    def login(
        self,
        payload: LoginRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> IssuedAuthTokens:
        user = self.users.get_by_identifier(payload.identifier)
        password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
        password_matches = self.verify_password(payload.password, password_hash)
        if user is None or user.status != "active" or not password_matches:
            raise AuthenticationError("账号或密码错误")

        user.last_login_at = self._now()
        tokens = self._issue_session(user, user_agent=user_agent, ip_address=ip_address)
        self.db.commit()
        self.db.refresh(user)
        return tokens

    def refresh(
        self,
        refresh_token: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> IssuedAuthTokens:
        now = self._now()
        record = self.refresh_sessions.get_by_hash_for_update(self.hash_refresh_token(refresh_token))
        if record is None:
            raise AuthenticationError("登录状态无效或已过期")

        if record.revoked_at is not None:
            if record.replaced_by_id is not None:
                self.refresh_sessions.revoke_family(record.family_id, now)
                self.db.commit()
            raise AuthenticationError("登录状态无效或已过期")

        if self._as_utc(record.expires_at) <= now:
            record.revoked_at = now
            self.db.commit()
            raise AuthenticationError("登录状态无效或已过期")

        user = self.users.get_by_id(record.user_id)
        if user is None or user.status != "active":
            record.revoked_at = now
            self.db.commit()
            raise AuthenticationError("登录状态无效或已过期")

        next_token = self.generate_refresh_token()
        next_record = self.refresh_sessions.create(
            {
                "user_id": user.id,
                "token_hash": self.hash_refresh_token(next_token),
                "family_id": record.family_id,
                "expires_at": now + timedelta(days=self.settings.auth_refresh_token_days),
                "user_agent": self._truncate(user_agent, 512),
                "ip_address": self._truncate(ip_address, 64),
            }
        )
        record.last_used_at = now
        record.revoked_at = now
        record.replaced_by_id = next_record.id
        self.db.commit()
        return IssuedAuthTokens(
            access_token=self.create_access_token(user),
            refresh_token=next_token,
            expires_in=self.access_token_seconds,
            user=user,
        )

    def logout(self, refresh_token: str | None, *, user_id: int) -> None:
        if refresh_token:
            record = self.refresh_sessions.get_by_hash_for_update(
                self.hash_refresh_token(refresh_token)
            )
            if record is not None and record.user_id == user_id and record.revoked_at is None:
                record.revoked_at = self._now()
        self.db.commit()

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not self.verify_password(current_password, user.password_hash):
            raise AuthenticationError("当前密码错误")
        user.password_hash = self.hash_password(new_password)
        user.auth_version += 1
        self.refresh_sessions.revoke_all_for_user(user.id, self._now())
        self.db.commit()

    def create_access_token(self, user: User) -> str:
        now = self._now()
        expires_at = now + timedelta(minutes=self.settings.auth_access_token_minutes)
        claims = {
            "sub": str(user.id),
            "typ": "access",
            "jti": uuid4().hex,
            "ver": user.auth_version,
            "iat": now,
            "exp": expires_at,
            "iss": self.settings.auth_issuer,
            "aud": self.settings.auth_audience,
        }
        return jwt.encode(claims, self.settings.auth_secret_key, algorithm="HS256")

    def decode_access_token(self, token: str) -> dict:
        try:
            claims = jwt.decode(
                token,
                self.settings.auth_secret_key,
                algorithms=["HS256"],
                issuer=self.settings.auth_issuer,
                audience=self.settings.auth_audience,
                options={"require": ["sub", "typ", "jti", "ver", "iat", "exp", "iss", "aud"]},
            )
        except InvalidTokenError as exc:
            raise AuthenticationError("登录状态无效或已过期") from exc
        if claims.get("typ") != "access":
            raise AuthenticationError("登录状态无效或已过期")
        return claims

    def hash_password(self, password: str) -> str:
        return self.password_hash.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            return self.password_hash.verify(password, password_hash)
        except Exception:
            return False

    @property
    def access_token_seconds(self) -> int:
        return self.settings.auth_access_token_minutes * 60

    @staticmethod
    def generate_refresh_token() -> str:
        return secrets.token_urlsafe(48)

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _issue_session(
        self,
        user: User,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> IssuedAuthTokens:
        refresh_token = self.generate_refresh_token()
        self.refresh_sessions.create(
            {
                "user_id": user.id,
                "token_hash": self.hash_refresh_token(refresh_token),
                "family_id": str(uuid4()),
                "expires_at": self._now()
                + timedelta(days=self.settings.auth_refresh_token_days),
                "user_agent": self._truncate(user_agent, 512),
                "ip_address": self._truncate(ip_address, 64),
            }
        )
        return IssuedAuthTokens(
            access_token=self.create_access_token(user),
            refresh_token=refresh_token,
            expires_in=self.access_token_seconds,
            user=user,
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _truncate(value: str | None, length: int) -> str | None:
        return value[:length] if value else None
