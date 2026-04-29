"""Telegram-flavoured HTML formatting for the three notification event types."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.notifications.channels.base import RenderedMessage
from app.notifications.events import (
    AUCTION_ALERTS,
    NEW_ITEMS,
    NotificationEvent,
    PRICE_DROPS,
    item_from_payload,
)

ITEM_PREVIEW_LIMIT = 5
AUCTION_BATCH_SIZE = 5


class TelegramFormatter:
    """Render notification events as HTML-formatted Telegram messages."""

    target_channel = "telegram"

    def format(
        self, event: NotificationEvent, payloads: list[Any]
    ) -> RenderedMessage:
        body = _BODY_BUILDERS[event.notification_type](event, payloads)
        return RenderedMessage(
            subject=_subject(event), body=body, body_format="html"
        )


def _subject(event: NotificationEvent) -> str:
    qt = event.query_text
    return {
        NEW_ITEMS: f"New items{_for(qt)}",
        PRICE_DROPS: f"Price drops{_for(qt)}",
        AUCTION_ALERTS: f"Auctions ending soon{_for(qt)}",
    }[event.notification_type]


def _for(query_text: str) -> str:
    return f" for '{query_text}'" if query_text else ""


def _build_new_items_body(event: NotificationEvent, payloads: list[Any]) -> str:
    qt = _for(event.query_text)
    lines = [
        f"🎉 <b>New Items Found{qt}!</b>",
        "",
        f"📥 Total new items: {len(payloads)}",
        "",
    ]
    for payload in payloads[:ITEM_PREVIEW_LIMIT]:
        item = item_from_payload(payload)
        lines.extend(_item_lines(item))
    return "\n".join(lines)


def _build_price_drops_body(event: NotificationEvent, payloads: list[Any]) -> str:
    qt = _for(event.query_text)
    lines = [f"🛎️ <b>Price drops{qt}</b>", ""]
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        item = payload.get("item")
        old_price = payload.get("old_price")
        new_price = payload.get("new_price")
        if item is None or old_price is None or new_price is None:
            continue
        lines.append(
            f"📦 <a href='{getattr(item, 'url', '')}'>{getattr(item, 'title', '')}</a>"
        )
        lines.append(f"💰 £{old_price} → £{new_price}")
        lines.append("")
    return "\n".join(lines)


def _build_auction_alerts_body(event: NotificationEvent, payloads: list[Any]) -> str:
    qt = _for(event.query_text)
    items = [item_from_payload(p) for p in payloads if item_from_payload(p) is not None]
    if not items:
        return f"⏳ <b>Auctions ending soon{qt}</b>"

    batches = [
        items[i : i + AUCTION_BATCH_SIZE]
        for i in range(0, len(items), AUCTION_BATCH_SIZE)
    ]
    sections: list[str] = []
    for batch in batches:
        section_lines = [f"⏳ <b>Auctions ending soon{qt}</b>", ""]
        for idx, item in enumerate(batch, 1):
            section_lines.extend(_auction_item_lines(idx, item))
        section_lines.append(f"Showing {len(batch)} of {len(items)} ending auctions")
        sections.append("\n".join(section_lines))
    return "\n\n".join(sections)


def _item_lines(item: Any) -> list[str]:
    title = getattr(item, "title", "(no title)")
    url = getattr(item, "url", "")
    price = getattr(item, "price", None)
    currency = getattr(item, "currency", "")
    location = getattr(item, "location_country", None) or "N/A"
    return [
        f"🏷️ <a href='{url}'>{title}</a>",
        f"💰 Price: {price} {currency}".strip(),
        f"📍 Location: {location}",
        "",
    ]


def _auction_item_lines(idx: int, item: Any) -> list[str]:
    title = getattr(item, "title", "(no title)")
    bid = getattr(item, "current_bid", None) or getattr(item, "price", None)
    bid_currency = getattr(item, "current_bid_currency", "") or getattr(
        item, "currency", ""
    )
    hours_left = _hours_until(getattr(item, "end_time", None))
    url = getattr(item, "url", "")
    return [
        f"{idx}. 📦 <b>{title}</b>",
        f"   💰 {bid} {bid_currency}".rstrip(),
        f"   ⏰ {hours_left}h left",
        f"   <a href='{url}'>View</a>",
        "",
    ]


def _hours_until(end_time: datetime | None) -> float:
    if end_time is None:
        return 0.0
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    delta = end_time - datetime.now(timezone.utc)
    return round(delta.total_seconds() / 3600, 1)


_BODY_BUILDERS: dict[str, Any] = {
    NEW_ITEMS: _build_new_items_body,
    PRICE_DROPS: _build_price_drops_body,
    AUCTION_ALERTS: _build_auction_alerts_body,
}
