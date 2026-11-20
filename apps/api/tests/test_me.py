from fastapi.testclient import TestClient

from app.models import User
from tests.conftest import auth_header


def test_me_returns_current_customer(client: TestClient, customer: User) -> None:
    """AUTH-5: GET /me returns {id, email, name, role} for a customer."""
    response = client.get("/me", headers=auth_header(customer))

    assert response.status_code == 200
    assert response.json() == {
        "id": str(customer.id),
        "email": "customer@example.com",
        "name": "Budi",
        "role": "customer",
    }


def test_me_returns_current_owner(client: TestClient, owner: User) -> None:
    """AUTH-5: GET /me works for the owner role too."""
    response = client.get("/me", headers=auth_header(owner))

    assert response.status_code == 200
    assert response.json()["role"] == "owner"


def test_me_never_returns_password_hash(client: TestClient, customer: User) -> None:
    """AUTH-5: the password hash is never part of the response."""
    response = client.get("/me", headers=auth_header(customer))

    assert "password_hash" not in response.text


def test_me_without_token_returns_401(client: TestClient) -> None:
    """AUTH-5: no access token → 401 UNAUTHENTICATED."""
    response = client.get("/me")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_me_rejects_refresh_token_as_bearer(client: TestClient, customer: User) -> None:
    """AUTH-5: an opaque refresh token is not an access token → 401 UNAUTHENTICATED."""
    tokens = client.post(
        "/auth/login", json={"email": "customer@example.com", "password": "correct-horse-battery"}
    ).json()

    response = client.get("/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
