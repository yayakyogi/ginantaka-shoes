"""Password hashing, JWT access tokens, opaque refresh tokens, reset codes (ADR 0003)."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"

_password_hash = PasswordHash((Argon2Hasher(),))
# Verified against when the email is unknown, so login takes the same time either way.
_DUMMY_HASH = _password_hash.hash("timing-equaliser-not-a-real-password")


class InvalidTokenError(Exception):
    """The access token is missing a claim, expired, forged, or not an access token."""


# --- Passwords ----------------------------------------------------------------------


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def verify_password_and_update(password: str, password_hash: str | None) -> tuple[bool, str | None]:
    """Verify and, if the stored hash uses outdated settings, return a new hash to save.

    With `password_hash=None` (unknown user) a dummy hash is checked and False is returned.
    """
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False, None
    return _password_hash.verify_and_update(password, password_hash)


# --- Access tokens (JWT) ------------------------------------------------------------


def create_access_token(user_id: UUID, role: str, *, now: datetime | None = None) -> str:
    settings = get_settings()
    issued_at = now or datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> UUID:
    """Return the user id from a valid access token, else raise InvalidTokenError."""
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload["type"] != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("not an access token")
    try:
        return UUID(payload["sub"])
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidTokenError("invalid subject") from exc


# --- Refresh tokens (opaque) --------------------------------------------------------


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hex digest. Refresh tokens are stored only in this form."""
    return hashlib.sha256(token.encode()).hexdigest()


# --- Password reset codes -----------------------------------------------------------


def generate_reset_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_reset_code(code: str) -> str:
    """HMAC-SHA256 keyed with JWT_SECRET.

    A 6-digit code has only 10^6 values, so a plain hash could be reversed from a leaked
    database in seconds. Keying it means the secret is needed as well.
    """
    return hmac.new(get_settings().jwt_secret.encode(), code.encode(), hashlib.sha256).hexdigest()


def reset_code_matches(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_reset_code(code), code_hash)
