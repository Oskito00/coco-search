"""Abstract notification formatter contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.notifications.channels.base import RenderedMessage
from app.notifications.events import NotificationEvent


class NotificationFormatter(ABC):
    """Render a domain event into a channel-specific :class:`RenderedMessage`."""

    target_channel: str

    @abstractmethod
    def format(
        self, event: NotificationEvent, payloads: list[Any]
    ) -> RenderedMessage:
        """Build the rendered message body for one event."""
