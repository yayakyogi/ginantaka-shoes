import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.security import hash_reset_code, hash_token, verify_password
from app.models import PasswordReset, RefreshToken, User
from tests.conftest import DEFAULT_PASSWORD, MakeUser
from tests.fakes import InMemoryEmailService

NEW_PASSWORD = "a-brand-new-password"


def _register(client: TestClient, **overrides: str) -> dict:
    body = {"email": "Siti@Example.com", "password": DEFAULT_PASSWORD, "name": "Siti"}
    body.update(overrides)
    return client.post("/auth/register", json=body).json()


def _login(client: TestClient, email: str, password: str = DEFAULT_PASSWORD) -> dict:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def _latest_code(outbox: InMemoryEmailService) -> str:
    match = re.search(r"\b(\d{6})\b", outbox.messages[-1].body)
    assert match, outbox.messages[-1].body
    return match.group(1)


def _only_reset(session: Session, user: User) -> PasswordReset:
    session.expire_all()
    return session.exec(select(PasswordReset).where(PasswordReset.user_id == user.id)).one()


# --- AUTH-1: register ---------------------------------------------------------------


def test_register_creates_customer_and_returns_tokens(client: TestClient, session: Session) -> None:
    """AUTH-1: register creates a customer and returns {user, access_token, refresh_token}."""
    response = client.post(
        "/auth/register",
        json={"email": "  Siti@Example.COM ", "password": DEFAULT_PASSWORD, "name": "Siti"},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"user", "access_token", "refresh_token"}
    assert set(body["user"]) == {"id", "email", "name", "role"}
    assert body["user"]["email"] == "siti@example.com"
    assert body["user"]["name"] == "Siti"
    assert body["user"]["role"] == "customer"
    assert UUID(body["user"]["id"]).version == 4

    user = session.exec(select(User).where(User.email == "siti@example.com")).one()
    assert user.password_hash != DEFAULT_PASSWORD
    assert verify_password(DEFAULT_PASSWORD, user.password_hash)


def test_register_tokens_are_usable(client: TestClient) -> None:
    """AUTH-1: the returned access token authenticates GET /me."""
    body = _register(client)

    response = client.get("/me", headers={"Authorization": f"Bearer {body['access_token']}"})

    assert response.status_code == 200
    assert response.json() == body["user"]


def test_register_duplicate_email_returns_409(client: TestClient, make_user: MakeUser) -> None:
    """AUTH-1: duplicate email (case-insensitive) → 409 EMAIL_ALREADY_REGISTERED."""
    make_user(email="siti@example.com")

    response = client.post(
        "/auth/register",
        json={"email": "SITI@example.com", "password": DEFAULT_PASSWORD, "name": "Siti"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_register_rejects_short_and_long_passwords(client: TestClient) -> None:
    """AUTH-1: password < 8 or > 128 chars → 422 VALIDATION_ERROR on `password`."""
    for password in ["x" * 7, "x" * 129]:
        response = client.post(
            "/auth/register",
            json={"email": "siti@example.com", "password": password, "name": "Siti"},
        )

        assert response.status_code == 422
        body = response.json()
        assert body["code"] == "VALIDATION_ERROR"
        assert [f["field"] for f in body["fields"]] == ["password"]


def test_register_accepts_password_length_boundaries(client: TestClient) -> None:
    """AUTH-1: passwords of exactly 8 and 128 chars are accepted."""
    for i, password in enumerate(["x" * 8, "x" * 128]):
        response = client.post(
            "/auth/register",
            json={"email": f"user{i}@example.com", "password": password, "name": "Siti"},
        )
        assert response.status_code == 201, response.text


def test_register_validates_email_and_name(client: TestClient) -> None:
    """AUTH-1: invalid email and blank or over-long name → 422 with each field listed."""
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": DEFAULT_PASSWORD, "name": "   "},
    )
    assert response.status_code == 422
    assert {f["field"] for f in response.json()["fields"]} == {"email", "name"}

    response = client.post(
        "/auth/register",
        json={"email": "siti@example.com", "password": DEFAULT_PASSWORD, "name": "n" * 101},
    )
    assert response.status_code == 422
    assert [f["field"] for f in response.json()["fields"]] == ["name"]


def test_register_cannot_choose_role(client: TestClient) -> None:
    """AUTH-1: a `role` in the body is ignored; registration always creates a customer."""
    response = client.post(
        "/auth/register",
        json={
            "email": "sneaky@example.com",
            "password": DEFAULT_PASSWORD,
            "name": "Sneaky",
            "role": "owner",
        },
    )

    assert response.status_code == 201
    assert response.json()["user"]["role"] == "customer"


# --- AUTH-2: login ------------------------------------------------------------------


def test_login_returns_user_and_tokens(client: TestClient, customer: User) -> None:
    """AUTH-2: valid credentials → 200 with {user, access_token, refresh_token}."""
    response = client.post(
        "/auth/login", json={"email": " CUSTOMER@example.com", "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"user", "access_token", "refresh_token"}
    assert body["user"] == {
        "id": str(customer.id),
        "email": "customer@example.com",
        "name": customer.name,
        "role": "customer",
    }


def test_login_works_for_owner(client: TestClient, owner: User) -> None:
    """AUTH-2: login is shared by both roles."""
    body = _login(client, "owner@example.com")
    assert body["user"]["role"] == "owner"


def test_login_wrong_password_or_unknown_email_returns_same_401(
    client: TestClient, customer: User
) -> None:
    """AUTH-2: wrong password and unknown email both → 401 INVALID_CREDENTIALS."""
    wrong_password = client.post(
        "/auth/login", json={"email": "customer@example.com", "password": "wrong-password"}
    )
    unknown_email = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": DEFAULT_PASSWORD}
    )

    for response in [wrong_password, unknown_email]:
        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_CREDENTIALS"
    assert wrong_password.json() == unknown_email.json()


# --- AUTH-3: refresh ----------------------------------------------------------------


def test_refresh_rotates_token_pair(client: TestClient, customer: User, session: Session) -> None:
    """AUTH-3: refresh revokes the used token and returns a new working pair."""
    tokens = _login(client, "customer@example.com")

    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "refresh_token"}
    assert body["refresh_token"] != tokens["refresh_token"]

    old = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(tokens["refresh_token"]))
    ).one()
    session.refresh(old)
    assert old.revoked_at is not None

    me = client.get("/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    again = client.post("/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert again.status_code == 200


def test_refresh_token_is_stored_only_as_hash(client: TestClient, session: Session) -> None:
    """AUTH-3: the refresh token itself is never stored, only its SHA-256 hash."""
    tokens = _register(client)

    stored = session.exec(select(RefreshToken)).all()

    assert len(stored) == 1
    assert stored[0].token_hash == hash_token(tokens["refresh_token"])
    assert stored[0].token_hash != tokens["refresh_token"]


def test_refresh_with_revoked_token_returns_401(client: TestClient, customer: User) -> None:
    """AUTH-3: reusing an already rotated token → 401 REFRESH_TOKEN_INVALID."""
    tokens = _login(client, "customer@example.com")
    client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 401
    assert response.json()["code"] == "REFRESH_TOKEN_INVALID"


def test_refresh_with_expired_token_returns_401(
    client: TestClient, customer: User, session: Session
) -> None:
    """AUTH-3: expired refresh token → 401 REFRESH_TOKEN_INVALID."""
    tokens = _login(client, "customer@example.com")
    stored = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(tokens["refresh_token"]))
    ).one()
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.add(stored)
    session.commit()

    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 401
    assert response.json()["code"] == "REFRESH_TOKEN_INVALID"


def test_refresh_with_unknown_token_returns_401(client: TestClient) -> None:
    """AUTH-3: unknown refresh token → 401 REFRESH_TOKEN_INVALID."""
    response = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})

    assert response.status_code == 401
    assert response.json()["code"] == "REFRESH_TOKEN_INVALID"


def test_refresh_token_expires_after_configured_days(
    client: TestClient, customer: User, session: Session
) -> None:
    """AUTH-3: refresh tokens are issued with a 30-day lifetime (REFRESH_TOKEN_TTL_DAYS)."""
    tokens = _login(client, "customer@example.com")
    stored = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(tokens["refresh_token"]))
    ).one()

    lifetime = stored.expires_at - datetime.now(UTC)
    assert timedelta(days=29, hours=23) < lifetime <= timedelta(days=30)


# --- AUTH-4: logout -----------------------------------------------------------------


def test_logout_revokes_refresh_token(client: TestClient, customer: User) -> None:
    """AUTH-4: logout → 204 and the refresh token no longer works."""
    tokens = _login(client, "customer@example.com")

    response = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 204
    assert response.content == b""
    refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401
    assert refresh.json()["code"] == "REFRESH_TOKEN_INVALID"


def test_logout_is_idempotent(client: TestClient, customer: User) -> None:
    """AUTH-4: logout with an already revoked or unknown token still returns 204."""
    tokens = _login(client, "customer@example.com")
    client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    again = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    unknown = client.post("/auth/logout", json={"refresh_token": "never-issued"})

    assert again.status_code == 204
    assert unknown.status_code == 204


def test_logout_only_revokes_the_given_token(client: TestClient, customer: User) -> None:
    """AUTH-4: other sessions of the same user keep working."""
    phone = _login(client, "customer@example.com")
    tablet = _login(client, "customer@example.com")

    client.post("/auth/logout", json={"refresh_token": phone["refresh_token"]})

    response = client.post("/auth/refresh", json={"refresh_token": tablet["refresh_token"]})
    assert response.status_code == 200


# --- AUTH-6: forgot password --------------------------------------------------------


def test_forgot_password_sends_six_digit_code(
    client: TestClient, customer: User, session: Session, email_outbox: InMemoryEmailService
) -> None:
    """AUTH-6: known email → 202, a 6-digit code is emailed and stored only as a hash."""
    response = client.post("/auth/password/forgot", json={"email": "Customer@Example.com"})

    assert response.status_code == 202
    assert len(email_outbox.messages) == 1
    assert email_outbox.messages[0].to == "customer@example.com"
    code = _latest_code(email_outbox)

    reset = _only_reset(session, customer)
    assert reset.code_hash != code
    assert reset.attempts == 0
    assert reset.used_at is None
    lifetime = reset.expires_at - datetime.now(UTC)
    assert timedelta(minutes=14) < lifetime <= timedelta(minutes=15)


def test_forgot_password_unknown_email_returns_202_without_email(
    client: TestClient, session: Session, email_outbox: InMemoryEmailService
) -> None:
    """AUTH-6: unknown email → same 202, nothing sent, nothing stored (no enumeration)."""
    response = client.post("/auth/password/forgot", json={"email": "nobody@example.com"})

    assert response.status_code == 202
    assert email_outbox.messages == []
    assert session.exec(select(PasswordReset)).all() == []


def test_forgot_password_invalidates_older_codes(
    client: TestClient, customer: User, session: Session, email_outbox: InMemoryEmailService
) -> None:
    """AUTH-6: requesting a new code marks older unused codes as used."""
    client.post("/auth/password/forgot", json={"email": "customer@example.com"})
    old_code = _latest_code(email_outbox)
    client.post("/auth/password/forgot", json={"email": "customer@example.com"})

    new_code = _latest_code(email_outbox)

    session.expire_all()
    resets = session.exec(select(PasswordReset).where(PasswordReset.user_id == customer.id)).all()
    assert len(resets) == 2
    assert sorted(r.used_at is None for r in resets) == [False, True]
    unused = next(r for r in resets if r.used_at is None)
    assert unused.code_hash == hash_reset_code(new_code)

    response = client.post(
        "/auth/password/reset",
        json={"email": "customer@example.com", "code": old_code, "new_password": NEW_PASSWORD},
    )
    if old_code != new_code:
        assert response.status_code == 400


# --- AUTH-7: reset password ---------------------------------------------------------


def _forgot(client: TestClient, outbox: InMemoryEmailService) -> str:
    client.post("/auth/password/forgot", json={"email": "customer@example.com"})
    return _latest_code(outbox)


def _reset(client: TestClient, code: str, email: str = "customer@example.com"):
    return client.post(
        "/auth/password/reset",
        json={"email": email, "code": code, "new_password": NEW_PASSWORD},
    )


def _wrong(code: str) -> str:
    return f"{(int(code) + 1) % 1_000_000:06d}"


def test_reset_password_success(
    client: TestClient, customer: User, session: Session, email_outbox: InMemoryEmailService
) -> None:
    """AUTH-7: correct code → 204, new password works, old one does not, code marked used."""
    code = _forgot(client, email_outbox)

    response = _reset(client, code)

    assert response.status_code == 204
    assert _only_reset(session, customer).used_at is not None
    _login(client, "customer@example.com", NEW_PASSWORD)
    old = client.post(
        "/auth/login", json={"email": "customer@example.com", "password": DEFAULT_PASSWORD}
    )
    assert old.status_code == 401


def test_reset_password_revokes_all_refresh_tokens(
    client: TestClient, customer: User, email_outbox: InMemoryEmailService
) -> None:
    """AUTH-7: a successful reset revokes every refresh token of the user."""
    phone = _login(client, "customer@example.com")
    tablet = _login(client, "customer@example.com")
    code = _forgot(client, email_outbox)

    assert _reset(client, code).status_code == 204

    for tokens in [phone, tablet]:
        response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert response.status_code == 401
        assert response.json()["code"] == "REFRESH_TOKEN_INVALID"


def test_reset_password_wrong_code_increments_attempts(
    client: TestClient, customer: User, session: Session, email_outbox: InMemoryEmailService
) -> None:
    """AUTH-7: wrong code → 400 RESET_CODE_INVALID and attempts goes up by one."""
    code = _forgot(client, email_outbox)

    response = _reset(client, _wrong(code))

    assert response.status_code == 400
    assert response.json()["code"] == "RESET_CODE_INVALID"
    assert _only_reset(session, customer).attempts == 1
    assert _reset(client, code).status_code == 204


def test_reset_password_unknown_email_returns_invalid_code(client: TestClient) -> None:
    """AUTH-7: unknown email → 400 RESET_CODE_INVALID."""
    response = _reset(client, "123456", email="nobody@example.com")

    assert response.status_code == 400
    assert response.json()["code"] == "RESET_CODE_INVALID"


def test_reset_password_without_requested_code_returns_invalid_code(
    client: TestClient, customer: User
) -> None:
    """AUTH-7: known email that never requested a code → 400 RESET_CODE_INVALID."""
    response = _reset(client, "123456")

    assert response.status_code == 400
    assert response.json()["code"] == "RESET_CODE_INVALID"


def test_reset_password_expired_code_returns_expired(
    client: TestClient, customer: User, session: Session, email_outbox: InMemoryEmailService
) -> None:
    """AUTH-7: correct but expired code → 400 RESET_CODE_EXPIRED."""
    code = _forgot(client, email_outbox)
    reset = _only_reset(session, customer)
    reset.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.add(reset)
    session.commit()

    response = _reset(client, code)

    assert response.status_code == 400
    assert response.json()["code"] == "RESET_CODE_EXPIRED"


def test_reset_password_used_code_returns_expired(
    client: TestClient, customer: User, email_outbox: InMemoryEmailService
) -> None:
    """AUTH-7: reusing a code that already reset the password → 400 RESET_CODE_EXPIRED."""
    code = _forgot(client, email_outbox)
    assert _reset(client, code).status_code == 204

    response = _reset(client, code)

    assert response.status_code == 400
    assert response.json()["code"] == "RESET_CODE_EXPIRED"


def test_reset_password_too_many_attempts_kills_code(
    client: TestClient, customer: User, session: Session, email_outbox: InMemoryEmailService
) -> None:
    """AUTH-7: the 5th failed attempt → 429 RESET_TOO_MANY_ATTEMPTS; the code stays dead."""
    code = _forgot(client, email_outbox)

    for _ in range(4):
        response = _reset(client, _wrong(code))
        assert response.status_code == 400
        assert response.json()["code"] == "RESET_CODE_INVALID"

    fifth = _reset(client, _wrong(code))
    assert fifth.status_code == 429
    assert fifth.json()["code"] == "RESET_TOO_MANY_ATTEMPTS"
    assert _only_reset(session, customer).attempts == 5

    correct_but_dead = _reset(client, code)
    assert correct_but_dead.status_code == 429
    assert correct_but_dead.json()["code"] == "RESET_TOO_MANY_ATTEMPTS"
    _login(client, "customer@example.com", DEFAULT_PASSWORD)


def test_reset_password_new_code_after_too_many_attempts(
    client: TestClient, customer: User, email_outbox: InMemoryEmailService
) -> None:
    """AUTH-7: after the code dies, requesting a new code allows the reset."""
    code = _forgot(client, email_outbox)
    for _ in range(5):
        _reset(client, _wrong(code))

    new_code = _forgot(client, email_outbox)

    assert _reset(client, new_code).status_code == 204


def test_reset_password_validates_new_password(
    client: TestClient, customer: User, email_outbox: InMemoryEmailService
) -> None:
    """AUTH-7: new_password < 8 chars → 422 VALIDATION_ERROR, code not consumed."""
    code = _forgot(client, email_outbox)

    response = client.post(
        "/auth/password/reset",
        json={"email": "customer@example.com", "code": code, "new_password": "short"},
    )

    assert response.status_code == 422
    assert [f["field"] for f in response.json()["fields"]] == ["new_password"]
    assert _reset(client, code).status_code == 204
