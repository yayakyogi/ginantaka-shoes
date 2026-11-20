from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, EmailStr, StringConstraints

from app.models import Role


def _normalize_email(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


# Emails are trimmed and compared lowercase everywhere (docs/data-model.md → users).
Email = Annotated[EmailStr, BeforeValidator(_normalize_email)]
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    role: Role


class RegisterRequest(BaseModel):
    email: Email
    password: Password
    name: Name


class LoginRequest(BaseModel):
    email: Email
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str


class AuthResponse(TokenPair):
    user: UserOut


class ForgotPasswordRequest(BaseModel):
    email: Email


class ResetPasswordRequest(BaseModel):
    email: Email
    code: str
    new_password: Password
