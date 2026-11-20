"""Column helpers shared by every table (docs/data-model.md).

Each helper builds a new Column per call: SQLAlchemy columns cannot be shared between tables,
so they cannot live on a mixin.
"""

from typing import Any
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Uuid, func, text
from sqlmodel import Field, SQLModel

SQLModel.metadata.naming_convention = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def id_field() -> Any:
    """`id uuid PRIMARY KEY DEFAULT gen_random_uuid()` (UUIDv4, ADR 0007).

    Python also generates the id, so it is known before the row is flushed.
    """
    return Field(
        default_factory=uuid4,
        sa_column=Column(Uuid, primary_key=True, server_default=text("gen_random_uuid()")),
    )


def created_at_field() -> Any:
    return Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )


def updated_at_field() -> Any:
    return Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
        ),
    )


def timestamptz_field() -> Any:
    return Field(sa_column=Column(DateTime(timezone=True), nullable=False))


def nullable_timestamptz_field() -> Any:
    return Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))


def user_fk_field() -> Any:
    """`user_id uuid NOT NULL REFERENCES users ON DELETE CASCADE`, indexed."""
    return Field(
        sa_column=Column(
            Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
