"""Account-linking flows for messaging channels.

A connector handles the lifecycle of binding a user's account to a delivery
channel (Telegram chat, WhatsApp number, ...). Delivery and rendering are
separate concerns — see :mod:`app.notifications.channels` and
:mod:`app.notifications.formatters`.
"""

from app.notifications.connectors.base import (
    LinkInstruction,
    LinkOutcome,
    MessagingConnector,
)
from app.notifications.connectors.telegram import (
    TelegramConnector,
    parse_start_command,
)
from app.notifications.connectors.tokens import LinkTokenService

__all__ = [
    "LinkInstruction",
    "LinkOutcome",
    "LinkTokenService",
    "MessagingConnector",
    "TelegramConnector",
    "parse_start_command",
]
