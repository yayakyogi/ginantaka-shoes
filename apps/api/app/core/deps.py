"""Authentication and authorization dependencies (ADR 0003).

`require_role` is the only place in the API that looks at `user.role`.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.db import get_session
from app.core.errors import AppError
from app.core.security import InvalidTokenError, decode_access_token
from app.models import Role, User

_bearer = HTTPBearer(auto_error=False)


def _unauthenticated() -> AppError:
    return AppError(
        401,
        "UNAUTHENTICATED",
        "Missing, invalid, or expired access token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    if credentials is None:
        raise _unauthenticated()
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise _unauthenticated() from exc

    user = session.get(User, user_id)
    if user is None:
        raise _unauthenticated()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role | str) -> Callable[[User], User]:
    """Dependency that returns the current user if their role is one of `roles`, else 403.

    The role comes from the database, not from the token claim.
    """
    allowed = {Role(role) for role in roles}

    def _require_role(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise AppError(403, "FORBIDDEN", "You do not have access to this resource.")
        return user

    return _require_role
