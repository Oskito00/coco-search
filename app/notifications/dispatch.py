"""Channel-pluggable dispatcher that routes events to formatters and channels.

The dispatcher's only job is composition:

    event -> [pick channels for user] -> formatter.format(event) -> channel.send(user, msg)

Adding a new channel (Google Chat, WhatsApp, ...) means registering one
``ChannelBinding`` here. The pipeline above does not change.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.notifications.channels import (
    DeliveryResult,
    EmailChannel,
    NotificationChannel,
    TelegramChannel,
)
from app.notifications.events import NotificationEvent
from app.notifications.formatters import (
    EmailFormatter,
    NotificationFormatter,
    TelegramFormatter,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChannelBinding:
    """Pairs a channel with the formatter that produces messages for it."""

    channel: NotificationChannel
    formatter: NotificationFormatter


class NotificationDispatcher:
    """Send a single event to every channel the user has enabled and connected."""

    def __init__(self, bindings: list[ChannelBinding] | None = None) -> None:
        self.bindings = bindings if bindings is not None else default_bindings()

    def dispatch(
        self,
        user: Any,
        event: NotificationEvent,
        payloads: list[Any],
    ) -> list[DeliveryResult]:
        """Render and send *event* to every available channel; return per-channel results."""
        results: list[DeliveryResult] = []
        for binding in self.bindings:
            if not binding.channel.is_available(user):
                continue
            try:
                message = binding.formatter.format(event, payloads)
            except Exception:  # noqa: BLE001 - formatters log and we treat as failure
                logger.exception(
                    "Formatter failed for channel %s", binding.channel.name
                )
                results.append(
                    DeliveryResult(
                        channel=binding.channel.name,
                        delivered=False,
                        detail="formatter_error",
                    )
                )
                continue
            results.append(binding.channel.send(user, message))
        return results


def default_bindings() -> list[ChannelBinding]:
    """Return the production channel/formatter pairs."""
    return [
        ChannelBinding(channel=TelegramChannel(), formatter=TelegramFormatter()),
        ChannelBinding(channel=EmailChannel(), formatter=EmailFormatter()),
    ]
