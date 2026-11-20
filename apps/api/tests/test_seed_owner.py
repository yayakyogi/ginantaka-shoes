import pytest
from sqlmodel import Session, select

from app.core.security import verify_password
from app.models import User
from app.scripts.seed_owner import SeedOwnerError, seed_owner
from tests.conftest import MakeUser


def test_seed_owner_creates_owner(session: Session) -> None:
    """CMD-1: creates an owner from OWNER_EMAIL / OWNER_PASSWORD / OWNER_NAME."""
    user = seed_owner(session, email=" Owner@Example.com ", password="owner-password", name="Ani")

    stored = session.exec(select(User).where(User.id == user.id)).one()
    assert stored.email == "owner@example.com"
    assert stored.name == "Ani"
    assert stored.role == "owner"
    assert verify_password("owner-password", stored.password_hash)


def test_seed_owner_fails_if_owner_exists(session: Session, owner: User) -> None:
    """CMD-1: fails if an owner already exists, and creates nothing."""
    with pytest.raises(SeedOwnerError, match="already exists"):
        seed_owner(session, email="second@example.com", password="owner-password", name="Dua")

    owners = session.exec(select(User).where(User.role == "owner")).all()
    assert [o.id for o in owners] == [owner.id]


def test_seed_owner_fails_if_email_taken_by_customer(session: Session, make_user: MakeUser) -> None:
    """CMD-1: an email already used by a customer is not turned into an owner."""
    make_user(email="owner@example.com", role="customer")

    with pytest.raises(SeedOwnerError, match="already registered"):
        seed_owner(session, email="owner@example.com", password="owner-password", name="Ani")


@pytest.mark.parametrize(
    ("email", "password", "name"),
    [
        (None, "owner-password", "Ani"),
        ("owner@example.com", None, "Ani"),
        ("owner@example.com", "owner-password", None),
        ("not-an-email", "owner-password", "Ani"),
        ("owner@example.com", "short", "Ani"),
        ("owner@example.com", "owner-password", "   "),
    ],
)
def test_seed_owner_rejects_missing_or_invalid_values(
    session: Session, email: str | None, password: str | None, name: str | None
) -> None:
    """CMD-1: missing or invalid OWNER_* values fail with a clear error."""
    with pytest.raises(SeedOwnerError):
        seed_owner(session, email=email, password=password, name=name)

    assert session.exec(select(User)).all() == []
