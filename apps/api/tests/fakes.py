from dataclasses import dataclass, field

from app.services.email import EmailMessage


@dataclass
class InMemoryEmailService:
    """Test double for EmailService: keeps sent messages instead of delivering them."""

    messages: list[EmailMessage] = field(default_factory=list)

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)
