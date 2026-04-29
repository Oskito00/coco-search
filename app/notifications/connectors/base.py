"""Connector contract for binding a user account to a messaging channel."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class LinkInstruction:
    """Frontend-facing payload that drives the user through a connect flow."""

    deep_link: str
    expires_at: datetime
    instructions: str


@dataclass(frozen=True)
class LinkOutcome:
    """Result of completing an account-linking handshake."""

    user_id: int
    channel: str
    delivered_confirmation: bool


class MessagingConnector(ABC):
    """Lifecycle for a messaging-channel account binding."""

    name: str

    @abstractmethod
    def start_link(self, user: Any) -> LinkInstruction:
        """Begin the connect flow (e.g. mint a token, return a deep link)."""

    @abstractmethod
    def disconnect(self, user: Any) -> None:
        """Forget the binding so further notifications stop."""

    @abstractmethod
    def is_connected(self, user: Any) -> bool:
        """Return True iff the user has an active binding for this channel."""
