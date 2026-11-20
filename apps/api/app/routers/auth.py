from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.core.errors import COMMON_RESPONSES, error_responses
from app.models import User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPair,
    UserOut,
)
from app.services import auth as auth_service
from app.services.email import EmailService, get_email_service

router = APIRouter(prefix="/auth", tags=["auth"], responses=COMMON_RESPONSES)

SessionDep = Annotated[Session, Depends(get_session)]


def _auth_response(user: User, tokens: TokenPair) -> AuthResponse:
    return AuthResponse(
        user=UserOut.model_validate(user, from_attributes=True),
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses=error_responses((409, "EMAIL_ALREADY_REGISTERED")),
)
def register(body: RegisterRequest, session: SessionDep) -> AuthResponse:
    """AUTH-1: create a customer account."""
    user, tokens = auth_service.register(
        session, email=body.email, password=body.password, name=body.name
    )
    return _auth_response(user, tokens)


@router.post("/login", responses=error_responses((401, "INVALID_CREDENTIALS")))
def login(body: LoginRequest, session: SessionDep) -> AuthResponse:
    """AUTH-2: log in as owner or customer."""
    user, tokens = auth_service.login(session, email=body.email, password=body.password)
    return _auth_response(user, tokens)


@router.post("/refresh", responses=error_responses((401, "REFRESH_TOKEN_INVALID")))
def refresh(body: RefreshTokenRequest, session: SessionDep) -> TokenPair:
    """AUTH-3: rotate the refresh token and get a new pair."""
    return auth_service.refresh(session, refresh_token=body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshTokenRequest, session: SessionDep) -> None:
    """AUTH-4: revoke a refresh token. Always 204."""
    auth_service.logout(session, refresh_token=body.refresh_token)


@router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    body: ForgotPasswordRequest,
    session: SessionDep,
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> None:
    """AUTH-6: email a 6-digit reset code if the account exists. Always 202."""
    auth_service.forgot_password(session, email_service, email=body.email)


@router.post(
    "/password/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(
        (400, "RESET_CODE_INVALID"),
        (400, "RESET_CODE_EXPIRED"),
        (429, "RESET_TOO_MANY_ATTEMPTS"),
    ),
)
def reset_password(body: ResetPasswordRequest, session: SessionDep) -> None:
    """AUTH-7: set a new password with the emailed code."""
    auth_service.reset_password(
        session, email=body.email, code=body.code, new_password=body.new_password
    )
