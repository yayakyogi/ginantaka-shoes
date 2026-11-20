from datetime import datetime
from uuid import UUID

from sqlalchemy import Integer, Text
from sqlmodel import Field, SQLModel

from app.models.base import (
    created_at_field,
    id_field,
    nullable_timestamptz_field,
    timestamptz_field,
    updated_at_field,
    user_fk_field,
)


class RefreshToken(SQLModel, table=True):
    """Opaque refresh token, stored only as a SHA-256 hash (ADR 0003)."""

    __tablename__ = "refresh_tokens"

    id: UUID = id_field()
    user_id: UUID = user_fk_field()
    token_hash: str = Field(sa_type=Text, unique=True)
    expires_at: datetime = timestamptz_field()
    revoked_at: datetime | None = nullable_timestamptz_field()
    created_at: datetime | None = created_at_field()
    updated_at: datetime | None = updated_at_field()


class PasswordReset(SQLModel, table=True):
    """6-digit reset code, stored only as a keyed hash (ADR 0003)."""

    __tablename__ = "password_resets"

    id: UUID = id_field()
    user_id: UUID = user_fk_field()
    code_hash: str = Field(sa_type=Text)
    expires_at: datetime = timestamptz_field()
    attempts: int = Field(default=0, sa_type=Integer, sa_column_kwargs={"server_default": "0"})
    used_at: datetime | None = nullable_timestamptz_field()
    created_at: datetime | None = created_at_field()
    updated_at: datetime | None = updated_at_field()
