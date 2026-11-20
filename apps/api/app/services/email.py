"""Outgoing email (ADR 0003). The production provider is an open decision."""

from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailService(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class ConsoleEmailService:
    """Development backend: prints the email to the API log instead of sending it."""

    def send(self, message: EmailMessage) -> None:
        print(
            f"\n--- email to {message.to} ---\nSubject: {message.subject}\n\n{message.body}\n"
            "--- end email ---\n",
            flush=True,
        )


def get_email_service() -> EmailService:
    """FastAPI dependency. Tests override it with an in-memory fake."""
    backend = get_settings().email_backend
    if backend == "console":
        return ConsoleEmailService()
    raise RuntimeError(f"Unsupported EMAIL_BACKEND: {backend}")


def password_reset_email(to: str, code: str, ttl_minutes: int) -> EmailMessage:
    return EmailMessage(
        to=to,
        subject="Kode reset kata sandi",
        body=(
            f"Kode reset kata sandi kamu: {code}\n\n"
            f"Kode ini berlaku {ttl_minutes} menit. "
            "Abaikan email ini jika kamu tidak meminta reset kata sandi."
        ),
    )
