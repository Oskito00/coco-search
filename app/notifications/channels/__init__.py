"""Delivery channels for notifications (Telegram, email, future WhatsApp...).

Each ``NotificationChannel`` knows how to push a ``RenderedMessage`` to a
single user. Channels are deliberately small: they do not render content or
manage account linking — those responsibilities live in
:mod:`app.notifications.formatters` and :mod:`app.notifications.connectors`.
"""

from app.notifications.channels.base import (
    DeliveryResult,
    NotificationChannel,
    RenderedMessage,
)
from app.notifications.channels.email import EmailChannel
from app.notifications.channels.telegram import TelegramChannel

__all__ = [
    "DeliveryResult",
    "EmailChannel",
    "NotificationChannel",
    "RenderedMessage",
    "TelegramChannel",
]
