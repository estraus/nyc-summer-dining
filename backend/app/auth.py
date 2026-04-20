from __future__ import annotations

import bcrypt
from itsdangerous import BadSignature, TimestampSigner

PRE_AUTH_COOKIE = "pre_auth"
SESSION_COOKIE = "session"
PRE_AUTH_TTL_SECONDS = 300
SESSION_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days


def hash_password(password: str) -> str:
    if not password or not password.strip():
        raise ValueError("password must not be empty")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        return False


def _signer(key: str, salt: str) -> TimestampSigner:
    return TimestampSigner(key, salt=salt)


def sign_pre_auth(key: str) -> str:
    return _signer(key, "pre-auth").sign(b"ok").decode("utf-8")


def verify_pre_auth(token: str, key: str) -> bool:
    try:
        _signer(key, "pre-auth").unsign(token, max_age=PRE_AUTH_TTL_SECONDS)
        return True
    except BadSignature:
        return False


def sign_session(user_id: int, display_name: str, key: str) -> str:
    payload = f"{user_id}:{display_name}".encode()
    return _signer(key, "session").sign(payload).decode("utf-8")


def read_session(token: str, key: str) -> tuple[int, str] | None:
    try:
        raw = _signer(key, "session").unsign(token, max_age=SESSION_TTL_SECONDS)
    except BadSignature:
        return None
    try:
        user_id_str, display_name = raw.decode("utf-8").split(":", 1)
        return int(user_id_str), display_name
    except (ValueError, UnicodeDecodeError):
        return None
