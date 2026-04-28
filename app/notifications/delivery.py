from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.notifications.events import (
    AUCTION_ALERTS,
    NEW_ITEMS,
    PRICE_DROPS,
    NotificationEvent,
)


@dataclass(frozen=True)
class RenderedNotification:
    """Rendered notification payload ready for delivery."""

    notification_type: str
    query_text: str
    payloads: list[Any]


class NotificationRenderer:
    """Prepare event payloads for the legacy delivery utilities."""

    def render(
        self,
        event: NotificationEvent,
        payloads: list[Any],
    ) -> RenderedNotification:
        """Return a delivery-ready notification."""
        return RenderedNotification(
            notification_type=event.notification_type,
            query_text=event.query_text,
            payloads=payloads,
        )


class NotificationSender:
    """Send notifications through existing Telegram/email utilities."""

    def __init__(self, manager: Any | None = None) -> None:
        if manager is None:
            from app.utils.notifications import NotificationManager

            manager = NotificationManager
        self.manager = manager

    def send(self, user: Any, notification: RenderedNotification) -> bool:
        """Send a rendered notification through the legacy manager."""
        if notification.notification_type == NEW_ITEMS:
            return bool(
                self.manager.send_item_notification(
                    user,
                    notification.payloads,
                    notification.query_text,
                )
            )
        if notification.notification_type == PRICE_DROPS:
            self.manager.send_price_drops(
                user,
                notification.payloads,
                notification.query_text,
            )
            return True
        if notification.notification_type == AUCTION_ALERTS:
            self.manager.send_auction_alerts(
                user,
                notification.payloads,
                notification.query_text,
            )
            return True
        return False
