from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, create_engine
from sqlmodel import Session

from app.core.config import API_ROOT, get_settings
from app.core.db import get_session
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import User
from app.services.email import get_email_service
from tests.fakes import InMemoryEmailService

DEFAULT_PASSWORD = "correct-horse-battery"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Engine for TEST_DATABASE_URL, migrated to head once per test run."""
    url = get_settings().test_database_url
    if not url:
        pytest.fail("TEST_DATABASE_URL is not set (see apps/api/.env.example)")

    alembic_cfg = Config(str(Path(API_ROOT) / "alembic.ini"))
    alembic_cfg.attributes["database_url"] = url
    command.upgrade(alembic_cfg, "head")

    test_engine = create_engine(url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def connection(engine: Engine) -> Iterator[Connection]:
    """One connection per test, wrapped in a transaction that is always rolled back."""
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            yield conn
        finally:
            transaction.rollback()


@pytest.fixture
def session(connection: Connection) -> Iterator[Session]:
    """Session bound to the test transaction. Commits become savepoints."""
    with Session(bind=connection, join_transaction_mode="create_savepoint") as db_session:
        yield db_session


@pytest.fixture
def email_outbox() -> InMemoryEmailService:
    """In-memory email backend; every sent message lands in `.messages`."""
    return InMemoryEmailService()


@pytest.fixture
def client(session: Session, email_outbox: InMemoryEmailService) -> Iterator[TestClient]:
    """HTTP client whose requests share the test's rolled-back session."""
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_email_service] = lambda: email_outbox
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


MakeUser = Callable[..., User]


@pytest.fixture
def make_user(session: Session) -> MakeUser:
    """Insert a user directly (bypassing the API) and return it."""

    def _make_user(
        email: str = "customer@example.com",
        password: str = DEFAULT_PASSWORD,
        name: str = "Budi",
        role: str = "customer",
    ) -> User:
        user = User(email=email, password_hash=hash_password(password), name=name, role=role)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    return _make_user


@pytest.fixture
def customer(make_user: MakeUser) -> User:
    return make_user()


@pytest.fixture
def owner(make_user: MakeUser) -> User:
    return make_user(email="owner@example.com", name="Pemilik", role="owner")


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}
