"""Importing this package registers every table on SQLModel.metadata (used by Alembic)."""

from app.models.auth import PasswordReset, RefreshToken
from app.models.user import Role, User

__all__ = ["PasswordReset", "RefreshToken", "Role", "User"]
