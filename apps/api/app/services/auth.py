"""Auth business logic (AUTH-1 … AUTH-7, ADR 0003). Routers only map HTTP to these calls."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select, update

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    generate_reset_code,
    hash_password,
    hash_reset_code,
    hash_token,
    reset_code_matches,
    verify_password_and_update,
)
from app.models import PasswordReset, RefreshToken, Role, User
from app.schemas.auth import TokenPair
from app.services.email import EmailService, password_reset_email

RESET_CODE_TTL_MINUTES = 15
RESET_CODE_MAX_ATTEMPTS = 5


def _now() -> datetime:
    return datetime.now(UTC)


def _issue_tokens(session: Session, user: User) -> TokenPair:
    """Create an access token and a new refresh token row. The caller commits."""
    refresh_token = generate_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=_now() + timedelta(days=get_settings().refresh_token_ttl_days),
        )
    )
    return TokenPair(
        access_token=create_access_token(user.id, user.role), refresh_token=refresh_token
    )


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()


def create_user(session: Session, *, email: str, password: str, name: str, role: Role) -> User:
    """Insert a user. Raises 409 EMAIL_ALREADY_REGISTERED if the email exists. Commits."""
    if get_user_by_email(session, email) is not None:
        raise _email_taken()
    user = User(email=email, password_hash=hash_password(password), name=name, role=role)
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:  # concurrent registration with the same email
        session.rollback()
        raise _email_taken() from exc
    return user


def _email_taken() -> AppError:
    return AppError(409, "EMAIL_ALREADY_REGISTERED", "This email is already registered.")


def register(session: Session, *, email: str, password: str, name: str) -> tuple[User, TokenPair]:
    """AUTH-1."""
    user = create_user(session, email=email, password=password, name=name, role=Role.CUSTOMER)
    tokens = _issue_tokens(session, user)
    session.commit()
    session.refresh(user)
    return user, tokens


def login(session: Session, *, email: str, password: str) -> tuple[User, TokenPair]:
    """AUTH-2. Wrong email and wrong password are indistinguishable."""
    user = get_user_by_email(session, email)
    valid, new_hash = verify_password_and_update(
        password, user.password_hash if user is not None else None
    )
    if user is None or not valid:
        raise AppError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")

    if new_hash is not None:
        user.password_hash = new_hash
        session.add(user)
    tokens = _issue_tokens(session, user)
    session.commit()
    session.refresh(user)
    return user, tokens


def refresh(session: Session, *, refresh_token: str) -> TokenPair:
    """AUTH-3. Rotation: the used token is revoked and a new pair is issued."""
    stored = session.exec(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(refresh_token))
        .with_for_update()
    ).first()
    now = _now()
    if stored is None or stored.revoked_at is not None or stored.expires_at <= now:
        raise AppError(401, "REFRESH_TOKEN_INVALID", "Refresh token is invalid or expired.")

    user = session.get(User, stored.user_id)
    assert user is not None  # FK with ON DELETE CASCADE
    stored.revoked_at = now
    session.add(stored)
    tokens = _issue_tokens(session, user)
    session.commit()
    return tokens


def logout(session: Session, *, refresh_token: str) -> None:
    """AUTH-4. Idempotent: unknown or already revoked tokens are ignored."""
    session.exec(
        update(RefreshToken)
        .where(col(RefreshToken.token_hash) == hash_token(refresh_token))
        .where(col(RefreshToken.revoked_at).is_(None))
        .values(revoked_at=_now())
    )
    session.commit()


def forgot_password(session: Session, email_service: EmailService, *, email: str) -> None:
    """AUTH-6. Silent for unknown emails (no account enumeration)."""
    user = get_user_by_email(session, email)
    if user is None:
        return

    now = _now()
    session.exec(
        update(PasswordReset)
        .where(col(PasswordReset.user_id) == user.id)
        .where(col(PasswordReset.used_at).is_(None))
        .values(used_at=now)
    )
    code = generate_reset_code()
    session.add(
        PasswordReset(
            user_id=user.id,
            code_hash=hash_reset_code(code),
            expires_at=now + timedelta(minutes=RESET_CODE_TTL_MINUTES),
        )
    )
    session.commit()
    email_service.send(password_reset_email(user.email, code, RESET_CODE_TTL_MINUTES))


def reset_password(session: Session, *, email: str, code: str, new_password: str) -> None:
    """AUTH-7. Only the user's unused code counts.

    `forgot_password` marks older codes used, so there is at most one unused code per user.
    """
    invalid = AppError(400, "RESET_CODE_INVALID", "The reset code is incorrect.")
    expired = AppError(400, "RESET_CODE_EXPIRED", "The reset code has expired. Request a new one.")
    too_many = AppError(
        429, "RESET_TOO_MANY_ATTEMPTS", "Too many incorrect attempts. Request a new code."
    )

    user = get_user_by_email(session, email)
    if user is None:
        raise invalid
    reset = session.exec(
        select(PasswordReset)
        .where(PasswordReset.user_id == user.id)
        .where(col(PasswordReset.used_at).is_(None))
        .with_for_update()
    ).first()
    if reset is None:
        has_used_code = session.exec(
            select(PasswordReset.id).where(PasswordReset.user_id == user.id).limit(1)
        ).first()
        raise expired if has_used_code is not None else invalid

    now = _now()
    if reset.expires_at <= now:
        raise expired
    if reset.attempts >= RESET_CODE_MAX_ATTEMPTS:
        raise too_many

    if not reset_code_matches(code, reset.code_hash):
        reset.attempts += 1
        session.add(reset)
        session.commit()
        raise too_many if reset.attempts >= RESET_CODE_MAX_ATTEMPTS else invalid

    user.password_hash = hash_password(new_password)
    reset.used_at = now
    session.add_all([user, reset])
    session.exec(
        update(RefreshToken)
        .where(col(RefreshToken.user_id) == user.id)
        .where(col(RefreshToken.revoked_at).is_(None))
        .values(revoked_at=now)
    )
    session.commit()
