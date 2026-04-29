"""Abstract delivery channel and the message contract every channel consumes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RenderedMessage:
    """Format-agnostic, channel-ready message produced by a formatter."""

    subject: str
    body: str
    body_format: str = "html"  # "html" | "text" | "markdown"
    attachments: tuple[Any, ...] = ()


@dataclass(frozen=True)
class DeliveryResult:
    """Outcome of dispatching one rendered message through one channel."""

    channel: str
    delivered: bool
    detail: str | None = None


class NotificationChannel(ABC):
    """Base class for any user-facing delivery surface."""

    name: str

    @abstractmethod
    def send(self, user: Any, message: RenderedMessage) -> DeliveryResult:
        """Push a rendered message to the given user."""

    def is_available(self, user: Any) -> bool:
        """Return True iff the channel can currently deliver to this user."""
        return True
