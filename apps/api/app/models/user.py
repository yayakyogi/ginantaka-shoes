from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, Text
from sqlmodel import Field, SQLModel

from app.models.base import created_at_field, id_field, updated_at_field


class Role(StrEnum):
    OWNER = "owner"
    CUSTOMER = "customer"


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('owner', 'customer')", name="role"),)

    id: UUID = id_field()
    email: str = Field(sa_type=Text, unique=True)  # stored lowercase and trimmed
    password_hash: str = Field(sa_type=Text)
    name: str = Field(sa_type=Text)
    role: str = Field(sa_type=Text)
    created_at: datetime | None = created_at_field()
    updated_at: datetime | None = updated_at_field()
