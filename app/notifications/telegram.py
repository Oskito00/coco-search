"""Backwards-compatible Telegram entry points used by legacy callers.

The real Telegram delivery lives in :class:`app.notifications.channels.TelegramChannel`.
This module exposes the small surface ``app/api/v1/notifications.py`` and
older tests still call: a single ``send_test_notification`` helper that pushes
either a connection confirmation or a probe message through the new channel.
"""

from __future__ import annotations

from typing import Any

from app.notifications.channels import RenderedMessage, TelegramChannel


class NotificationManager:
    """Static helpers preserved for backwards compatibility."""

    @staticmethod
    def send_test_notification(
        user: Any, is_successfull_connection: bool = False
    ) -> bool:
        """Send a probe (or confirmation) message to the user's Telegram chats."""
        message = _build_test_message(is_successfull_connection)
        result = TelegramChannel().send(user, message)
        return bool(result.delivered)


def _build_test_message(is_successfull_connection: bool) -> RenderedMessage:
    if is_successfull_connection:
        body = "✅ <b>Your account has been successfully connected!</b>"
    else:
        body = "<b>Coco Search</b> — test notification (TESTING TESTING 123...)"
    return RenderedMessage(
        subject="Coco Search test notification",
        body=body,
        body_format="html",
    )
