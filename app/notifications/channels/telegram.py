"""Telegram channel: push a rendered message to a user's connected chats."""

from __future__ import annotations

import logging
from typing import Any, Callable, Iterable

import requests
from flask import current_app

from app.notifications.channels.base import (
    DeliveryResult,
    NotificationChannel,
    RenderedMessage,
)

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org"


class TelegramChannel(NotificationChannel):
    """Send messages to a user's main + additional Telegram chats."""

    name = "telegram"

    def __init__(
        self,
        bot_token_provider: Callable[[], str | None] | None = None,
        http: Any | None = None,
    ) -> None:
        self.bot_token_provider = bot_token_provider or _bot_token_from_app
        self.http = http or requests

    def is_available(self, user: Any) -> bool:
        return bool(getattr(user, "telegram_connected", False)) and bool(
            _user_chat_ids(user)
        )

    def send(self, user: Any, message: RenderedMessage) -> DeliveryResult:
        if not self.is_available(user):
            return DeliveryResult(self.name, delivered=False, detail="not_connected")

        token = self.bot_token_provider()
        if not token:
            return DeliveryResult(self.name, delivered=False, detail="missing_token")

        chat_ids = list(_user_chat_ids(user))
        delivered_count = sum(
            1 for chat_id in chat_ids if self._post(token, chat_id, message)
        )
        return DeliveryResult(
            channel=self.name,
            delivered=delivered_count > 0,
            detail=f"delivered={delivered_count}/{len(chat_ids)}",
        )

    def _post(self, token: str, chat_id: str, message: RenderedMessage) -> bool:
        try:
            response = self.http.post(
                f"{TELEGRAM_API_URL}/bot{token}/sendMessage",
                json=_build_payload(chat_id, message),
                timeout=10,
            )
        except Exception:  # noqa: BLE001 - network errors logged & treated as failure
            logger.exception("Telegram send failed for chat %s", chat_id)
            return False
        return getattr(response, "status_code", 0) == 200


def _build_payload(chat_id: str, message: RenderedMessage) -> dict[str, Any]:
    parse_mode = "HTML" if message.body_format == "html" else "Markdown"
    return {
        "chat_id": chat_id,
        "text": message.body,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }


def _bot_token_from_app() -> str | None:
    return current_app.config.get("TELEGRAM_BOT_TOKEN")


def _user_chat_ids(user: Any) -> Iterable[str]:
    chat_ids = getattr(user, "telegram_chat_ids", None) or {}
    main = chat_ids.get("main")
    additional = chat_ids.get("additional") or []
    if main:
        yield str(main)
    for chat_id in additional:
        if chat_id:
            yield str(chat_id)
