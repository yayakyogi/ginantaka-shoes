"""CMD-1: create the owner account from OWNER_EMAIL, OWNER_PASSWORD, OWNER_NAME.

Usage: python -m app.scripts.seed_owner   (or `task api:seed-owner`)
"""

import sys

from pydantic import BaseModel, ValidationError
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.db import engine
from app.core.errors import AppError
from app.models import Role, User
from app.schemas.auth import Email, Name, Password
from app.services.auth import create_user


class SeedOwnerError(Exception):
    pass


class _OwnerInput(BaseModel):
    email: Email
    password: Password
    name: Name


def seed_owner(
    session: Session, *, email: str | None, password: str | None, name: str | None
) -> User:
    """Create the owner. Raises SeedOwnerError if values are invalid or an owner exists."""
    missing = [
        var
        for var, value in [
            ("OWNER_EMAIL", email),
            ("OWNER_PASSWORD", password),
            ("OWNER_NAME", name),
        ]
        if not value
    ]
    if missing:
        raise SeedOwnerError(f"Missing env vars: {', '.join(missing)}")
    try:
        owner_input = _OwnerInput(email=email, password=password, name=name)
    except ValidationError as exc:
        details = "; ".join(f"{e['loc'][0]}: {e['msg']}" for e in exc.errors())
        raise SeedOwnerError(f"Invalid OWNER_* values: {details}") from exc

    if session.exec(select(User).where(User.role == Role.OWNER)).first() is not None:
        raise SeedOwnerError("An owner already exists. Only one owner is allowed.")
    try:
        user = create_user(
            session,
            email=owner_input.email,
            password=owner_input.password,
            name=owner_input.name,
            role=Role.OWNER,
        )
    except AppError as exc:
        raise SeedOwnerError(f"{owner_input.email} is already registered.") from exc
    session.commit()
    session.refresh(user)
    return user


def main() -> None:
    settings = get_settings()
    with Session(engine) as session:
        try:
            user = seed_owner(
                session,
                email=settings.owner_email,
                password=settings.owner_password,
                name=settings.owner_name,
            )
        except SeedOwnerError as exc:
            sys.exit(f"seed-owner failed: {exc}")
    print(f"Owner created: {user.email} (id {user.id})")


if __name__ == "__main__":
    main()
