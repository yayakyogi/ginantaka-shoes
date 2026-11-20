"""require_role / get_current_user, exercised through a test-only app (never the real one)."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import get_settings
from app.core.db import get_session
from app.core.deps import require_role
from app.core.errors import register_error_handlers
from app.core.security import create_access_token
from app.models import User
from tests.conftest import auth_header


@pytest.fixture
def guarded_client(session: Session) -> Iterator[TestClient]:
    test_app = FastAPI()
    register_error_handlers(test_app)

    @test_app.get("/owner-only")
    def owner_only(user: Annotated[User, Depends(require_role("owner"))]) -> dict[str, str]:
        return {"id": str(user.id)}

    @test_app.get("/customer-only")
    def customer_only(
        user: Annotated[User, Depends(require_role("customer"))],
    ) -> dict[str, str]:
        return {"id": str(user.id)}

    @test_app.get("/either")
    def either(
        user: Annotated[User, Depends(require_role("owner", "customer"))],
    ) -> dict[str, str]:
        return {"id": str(user.id)}

    test_app.dependency_overrides[get_session] = lambda: session
    with TestClient(test_app) as test_client:
        yield test_client


def _assert_401(response) -> None:
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
    assert set(response.json()) == {"code", "message"}


def test_require_role_allows_matching_role(
    guarded_client: TestClient, owner: User, customer: User
) -> None:
    """AUTH-5 (require_role, ADR 0003): a token with an allowed role passes."""
    assert guarded_client.get("/owner-only", headers=auth_header(owner)).json() == {
        "id": str(owner.id)
    }
    assert guarded_client.get("/customer-only", headers=auth_header(customer)).status_code == 200
    assert guarded_client.get("/either", headers=auth_header(owner)).status_code == 200
    assert guarded_client.get("/either", headers=auth_header(customer)).status_code == 200


def test_require_role_without_token_returns_401(guarded_client: TestClient) -> None:
    """AUTH-5 (require_role): no Authorization header → 401 UNAUTHENTICATED."""
    _assert_401(guarded_client.get("/owner-only"))


def test_require_role_with_expired_token_returns_401(
    guarded_client: TestClient, owner: User
) -> None:
    """AUTH-5 (require_role): expired access token → 401 UNAUTHENTICATED."""
    issued = datetime.now(UTC) - timedelta(minutes=get_settings().access_token_ttl_minutes + 1)
    token = create_access_token(owner.id, owner.role, now=issued)

    _assert_401(guarded_client.get("/owner-only", headers={"Authorization": f"Bearer {token}"}))


def test_require_role_with_malformed_token_returns_401(guarded_client: TestClient) -> None:
    """AUTH-5 (require_role): malformed token or wrong scheme → 401 UNAUTHENTICATED."""
    for header in ["Bearer not-a-jwt", "Basic dXNlcjpwYXNz", "Bearer", "garbage"]:
        _assert_401(guarded_client.get("/owner-only", headers={"Authorization": header}))


def test_require_role_with_forged_signature_returns_401(
    guarded_client: TestClient, owner: User
) -> None:
    """AUTH-5 (require_role): a token signed with another secret → 401 UNAUTHENTICATED."""
    now = datetime.now(UTC)
    forged = jwt.encode(
        {
            "sub": str(owner.id),
            "role": "owner",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        "not-the-real-secret-but-long-enough-for-hs256",
        algorithm="HS256",
    )

    _assert_401(guarded_client.get("/owner-only", headers={"Authorization": f"Bearer {forged}"}))


def test_require_role_with_non_access_token_type_returns_401(
    guarded_client: TestClient, owner: User
) -> None:
    """AUTH-5 (require_role): a JWT whose `type` is not "access" → 401 UNAUTHENTICATED."""
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(owner.id),
            "role": "owner",
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )

    _assert_401(guarded_client.get("/owner-only", headers={"Authorization": f"Bearer {token}"}))


def test_require_role_with_non_uuid_subject_returns_401(guarded_client: TestClient) -> None:
    """AUTH-5 (require_role): a correctly signed token whose `sub` is not a UUID → 401."""
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "1",
            "role": "owner",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )

    _assert_401(guarded_client.get("/owner-only", headers={"Authorization": f"Bearer {token}"}))


def test_require_role_with_deleted_user_returns_401(
    guarded_client: TestClient, owner: User, session: Session
) -> None:
    """AUTH-5 (require_role): a valid token for a user that no longer exists → 401."""
    headers = auth_header(owner)
    session.delete(owner)
    session.commit()

    _assert_401(guarded_client.get("/owner-only", headers=headers))


def test_require_role_with_wrong_role_returns_403(
    guarded_client: TestClient, owner: User, customer: User
) -> None:
    """AUTH-5 (require_role): valid token, wrong role → 403 FORBIDDEN."""
    for path, user in [("/owner-only", customer), ("/customer-only", owner)]:
        response = guarded_client.get(path, headers=auth_header(user))

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"


def test_require_role_uses_database_role_not_token_claim(
    guarded_client: TestClient, customer: User
) -> None:
    """AUTH-5 (require_role): a customer token claiming `owner` is still forbidden."""
    token = create_access_token(customer.id, "owner")

    response = guarded_client.get("/owner-only", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
