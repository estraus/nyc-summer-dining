from __future__ import annotations

import math

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth import (
    PRE_AUTH_COOKIE,
    PRE_AUTH_TTL_SECONDS,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    sign_pre_auth,
    sign_session,
    verify_password,
    verify_pre_auth,
)
from app.config import get_settings
from app.rate_limit import SlidingWindowLimiter
from app.users import create_user, list_users

router = APIRouter(prefix="/api/login", tags=["auth"])

_login_limiter: SlidingWindowLimiter | None = None


def _get_login_limiter() -> SlidingWindowLimiter:
    global _login_limiter
    if _login_limiter is None:
        settings = get_settings()
        _login_limiter = SlidingWindowLimiter(
            max_attempts=settings.login_rate_limit,
            window_seconds=settings.login_rate_window_seconds,
        )
    return _login_limiter


def _reset_login_limiter() -> None:  # pyright: ignore[reportUnusedFunction]
    """Test hook: rebuild the limiter so per-test settings take effect."""
    global _login_limiter
    _login_limiter = None


def _client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host or "unknown"


class VerifyPasswordRequest(BaseModel):
    password: str = Field(min_length=1)


class CompleteLoginRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)


class OkResponse(BaseModel):
    ok: bool = True


class CompleteLoginResponse(BaseModel):
    user_id: int
    display_name: str


class ListUsersResponse(BaseModel):
    users: list[CompleteLoginResponse]


@router.post("/verify-password", response_model=OkResponse)
def verify_password_endpoint(
    body: VerifyPasswordRequest, request: Request, response: Response
) -> OkResponse:
    settings = get_settings()
    retry_after = _get_login_limiter().check(_client_ip(request))
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="rate_limited",
            headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
        )
    if not verify_password(body.password, settings.shared_password_hash):
        raise HTTPException(status_code=401, detail="bad_password")
    token = sign_pre_auth(settings.cookie_signing_key)
    response.set_cookie(
        PRE_AUTH_COOKIE,
        token,
        max_age=PRE_AUTH_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return OkResponse()


@router.post("/complete", response_model=CompleteLoginResponse)
def complete_login(
    body: CompleteLoginRequest,
    response: Response,
    pre_auth: str | None = Cookie(default=None),
) -> CompleteLoginResponse:
    settings = get_settings()
    if not pre_auth or not verify_pre_auth(pre_auth, settings.cookie_signing_key):
        raise HTTPException(status_code=401, detail="missing_pre_auth")
    try:
        user = create_user(settings.db_path, body.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_name") from exc
    token = sign_session(user.id, user.display_name, settings.cookie_signing_key)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    response.delete_cookie(PRE_AUTH_COOKIE)
    return CompleteLoginResponse(user_id=user.id, display_name=user.display_name)


@router.get("/users", response_model=ListUsersResponse)
def list_users_endpoint(pre_auth: str | None = Cookie(default=None)) -> ListUsersResponse:
    settings = get_settings()
    if not pre_auth or not verify_pre_auth(pre_auth, settings.cookie_signing_key):
        raise HTTPException(status_code=401, detail="missing_pre_auth")
    users = list_users(settings.db_path)
    return ListUsersResponse(
        users=[CompleteLoginResponse(user_id=u.id, display_name=u.display_name) for u in users]
    )
