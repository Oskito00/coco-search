"""Email-flavoured HTML formatting for the three notification event types."""

from __future__ import annotations

from typing import Any

from app.notifications.channels.base import RenderedMessage
from app.notifications.events import (
    AUCTION_ALERTS,
    NEW_ITEMS,
    NotificationEvent,
    PRICE_DROPS,
    item_from_payload,
)


class EmailFormatter:
    """Render notification events as HTML email bodies."""

    target_channel = "email"

    def format(
        self, event: NotificationEvent, payloads: list[Any]
    ) -> RenderedMessage:
        subject, body = _RENDERERS[event.notification_type](event, payloads)
        return RenderedMessage(subject=subject, body=body, body_format="html")


def _render_new_items(
    event: NotificationEvent, payloads: list[Any]
) -> tuple[str, str]:
    subject = _subject_for("New items", event.query_text)
    items_html = "".join(_item_html(item_from_payload(p)) for p in payloads)
    body = _wrap_body(
        f"<h2>{subject}</h2><p>{len(payloads)} new items.</p>{items_html}"
    )
    return subject, body


def _render_price_drops(
    event: NotificationEvent, payloads: list[Any]
) -> tuple[str, str]:
    subject = _subject_for("Price drops", event.query_text)
    rows = "".join(
        _price_drop_row(p) for p in payloads if isinstance(p, dict)
    )
    body = _wrap_body(f"<h2>{subject}</h2>{rows}")
    return subject, body


def _render_auction_alerts(
    event: NotificationEvent, payloads: list[Any]
) -> tuple[str, str]:
    subject = _subject_for("Auctions ending soon", event.query_text)
    items_html = "".join(_item_html(item_from_payload(p)) for p in payloads)
    body = _wrap_body(f"<h2>{subject}</h2>{items_html}")
    return subject, body


def _subject_for(prefix: str, query_text: str) -> str:
    if query_text:
        return f"{prefix} for '{query_text}'"
    return prefix


def _item_html(item: Any) -> str:
    if item is None:
        return ""
    title = getattr(item, "title", "(no title)")
    url = getattr(item, "url", "#")
    price = getattr(item, "price", None)
    currency = getattr(item, "currency", "")
    return (
        "<div style='margin-bottom:12px'>"
        f"<a href='{url}'><strong>{title}</strong></a><br>"
        f"{price} {currency}"
        "</div>"
    )


def _price_drop_row(payload: dict[str, Any]) -> str:
    item = payload.get("item")
    if item is None:
        return ""
    title = getattr(item, "title", "(no title)")
    url = getattr(item, "url", "#")
    return (
        "<div style='margin-bottom:12px'>"
        f"<a href='{url}'><strong>{title}</strong></a><br>"
        f"£{payload.get('old_price')} → £{payload.get('new_price')}"
        "</div>"
    )


def _wrap_body(content: str) -> str:
    return (
        "<html><body style='font-family:sans-serif;max-width:560px'>"
        f"{content}"
        "</body></html>"
    )


_RENDERERS = {
    NEW_ITEMS: _render_new_items,
    PRICE_DROPS: _render_price_drops,
    AUCTION_ALERTS: _render_auction_alerts,
}
