from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.auth import (
    PRE_AUTH_COOKIE,
    PRE_AUTH_TTL_SECONDS,
    sign_pre_auth,
    verify_password,
)
from app.config import get_settings

router = APIRouter(prefix="/api/login", tags=["auth"])


class VerifyPasswordRequest(BaseModel):
    password: str = Field(min_length=1)


class OkResponse(BaseModel):
    ok: bool = True


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
