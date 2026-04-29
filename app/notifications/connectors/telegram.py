"""Telegram connect flow: deep-link handshake -> webhook -> chat-id capture.

The user clicks one button. The frontend opens ``t.me/<bot>?start=<token>``,
the user taps "Start", Telegram delivers an update to our webhook, and the
connector records the chat id and confirms back to the user. No copy-paste.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from flask import current_app

from app.notifications.channels.base import RenderedMessage
from app.notifications.channels.telegram import TelegramChannel
from app.notifications.connectors.base import (
    LinkInstruction,
    LinkOutcome,
    MessagingConnector,
)
from app.notifications.connectors.tokens import LinkTokenService

logger = logging.getLogger(__name__)

CONNECTOR_KIND = "telegram"
START_COMMAND_PREFIX = "/start "
DEFAULT_INSTRUCTIONS = (
    "Tap the button to open Telegram and press Start. "
    "We'll handle the rest."
)


class TelegramConnector(MessagingConnector):
    """Mint deep links, accept webhook updates, and record chat-id bindings."""

    name = CONNECTOR_KIND

    def __init__(
        self,
        token_service: LinkTokenService | None = None,
        bot_username_provider: Callable[[], str | None] | None = None,
        user_repository: Any | None = None,
        session: Any | None = None,
        channel: TelegramChannel | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.tokens = token_service or LinkTokenService()
        self.bot_username_provider = bot_username_provider or _bot_username_from_app
        self.users = user_repository or _DefaultUserRepository()
        self.session = session or _default_session()
        self.channel = channel or TelegramChannel()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------------ start
    def start_link(self, user: Any) -> LinkInstruction:
        """Mint a signed token and return the deep link the frontend should open."""
        token = self.tokens.mint(user.id, kind=CONNECTOR_KIND)
        bot_username = self._require_bot_username()
        deep_link = f"https://t.me/{bot_username}?start={token}"
        return LinkInstruction(
            deep_link=deep_link,
            expires_at=self.clock() + timedelta(seconds=self.tokens.ttl_seconds),
            instructions=DEFAULT_INSTRUCTIONS,
        )

    # ------------------------------------------------------------------ finish
    def finish_link(
        self, token: str, chat_id: str, send_confirmation: bool = True
    ) -> Optional[LinkOutcome]:
        """Validate *token*, store *chat_id* on the user, optionally confirm in-chat."""
        user_id = self.tokens.verify(token, kind=CONNECTOR_KIND)
        if user_id is None:
            return None

        user = self.users.get(user_id)
        if user is None:
            return None

        self._bind_chat(user, str(chat_id))
        delivered = (
            self._send_confirmation(user) if send_confirmation else False
        )
        return LinkOutcome(
            user_id=int(user_id),
            channel=self.name,
            delivered_confirmation=delivered,
        )

    # ------------------------------------------------------------------ status
    def is_connected(self, user: Any) -> bool:
        return bool(getattr(user, "telegram_connected", False)) and bool(
            (getattr(user, "telegram_chat_ids", None) or {}).get("main")
        )

    def disconnect(self, user: Any) -> None:
        user.telegram_chat_ids = {"main": None, "additional": []}
        user.telegram_connected = False
        self.session.commit()

    # ------------------------------------------------------------------ internals
    def _bind_chat(self, user: Any, chat_id: str) -> None:
        chat_ids = dict(getattr(user, "telegram_chat_ids", None) or {})
        existing_main = chat_ids.get("main")
        if existing_main and existing_main != chat_id:
            additional = list(chat_ids.get("additional") or [])
            if chat_id not in additional and chat_id != existing_main:
                additional.append(chat_id)
            chat_ids["additional"] = additional
        else:
            chat_ids["main"] = chat_id
            chat_ids.setdefault("additional", [])
        user.telegram_chat_ids = chat_ids
        user.telegram_connected = True
        self.session.commit()

    def _send_confirmation(self, user: Any) -> bool:
        message = RenderedMessage(
            subject="Coco Search — connected",
            body="✅ <b>Connected!</b>\nYou'll start receiving notifications here.",
            body_format="html",
        )
        result = self.channel.send(user, message)
        return result.delivered

    def _require_bot_username(self) -> str:
        username = self.bot_username_provider()
        if not username:
            raise RuntimeError(
                "TELEGRAM_BOT_USERNAME is not configured; cannot build a deep link."
            )
        return username


def parse_start_command(text: Optional[str]) -> Optional[str]:
    """Extract the linking token from a Telegram ``/start <token>`` payload."""
    if not text or not text.startswith(START_COMMAND_PREFIX):
        return None
    token = text[len(START_COMMAND_PREFIX) :].strip()
    return token or None


def _bot_username_from_app() -> str | None:
    return current_app.config.get("TELEGRAM_BOT_USERNAME")


def _default_session() -> Any:
    from app.extensions import db

    return db.session


class _DefaultUserRepository:
    """Tiny adapter that loads ``User`` rows by primary key."""

    def get(self, user_id: int) -> Any:
        from app.models import User

        return User.query.get(user_id)
