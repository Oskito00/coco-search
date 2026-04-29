"""Email channel: deliver a rendered message via Flask-Mail."""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.notifications.channels.base import (
    DeliveryResult,
    NotificationChannel,
    RenderedMessage,
)

logger = logging.getLogger(__name__)


class EmailChannel(NotificationChannel):
    """Push a rendered message to the user's confirmed email address."""

    name = "email"

    def __init__(
        self, mailer: Callable[[str, str, str], None] | None = None
    ) -> None:
        self.mailer = mailer or _default_mailer

    def is_available(self, user: Any) -> bool:
        return bool(
            getattr(user, "email", None) and getattr(user, "confirmed", False)
        )

    def send(self, user: Any, message: RenderedMessage) -> DeliveryResult:
        if not self.is_available(user):
            return DeliveryResult(self.name, delivered=False, detail="email_unavailable")

        try:
            self.mailer(user.email, message.subject, message.body)
        except Exception as exc:  # noqa: BLE001 - log and treat as failure
            logger.exception("Email send failed")
            return DeliveryResult(self.name, delivered=False, detail=str(exc))
        return DeliveryResult(self.name, delivered=True)


def _default_mailer(to: str, subject: str, body: str) -> None:
    from app.utils.email import send_email

    send_email(to=to, subject=subject, template=body)
