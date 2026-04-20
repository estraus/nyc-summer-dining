from __future__ import annotations

from fastapi import APIRouter, Cookie, HTTPException, Response
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
from app.users import create_user, list_users

router = APIRouter(prefix="/api/login", tags=["auth"])


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
def verify_password_endpoint(body: VerifyPasswordRequest, response: Response) -> OkResponse:
    settings = get_settings()
    if not verify_password(body.password, settings.shared_password_hash):
        raise HTTPException(status_code=401, detail="bad_password")
    token = sign_pre_auth(settings.cookie_signing_key)
    response.set_cookie(
        PRE_AUTH_COOKIE,
        token,
        max_age=PRE_AUTH_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,
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
        secure=False,
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
