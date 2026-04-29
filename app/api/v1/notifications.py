"""Notification preferences + Telegram connect-flow API.

The legacy ``PUT /telegram`` chat-id paste route is kept for now so existing
clients keep working, but the recommended flow is the deep-link handshake:
``POST /telegram/start-link`` -> open Telegram -> webhook completes binding.
"""

from __future__ import annotations

from flask import Blueprint, g

from app.api.errors import BadRequest
from app.api.middleware import require_auth
from app.api.responses import ok
from app.api.schemas import Field, get_json, validate
from app.auth import SCOPE_NOTIFICATIONS_READ, SCOPE_NOTIFICATIONS_WRITE
from app.extensions import db
from app.notifications.connectors import TelegramConnector
from app.notifications.telegram import NotificationManager

bp = Blueprint("notifications", __name__, url_prefix="/notifications")

_PREF_KEYS = {"price_drops", "new_items", "auction_alerts"}

_PREFS_SCHEMA = {
    "price_drops": Field(bool, default=None),
    "new_items": Field(bool, default=None),
    "auction_alerts": Field(bool, default=None),
}

_TELEGRAM_SCHEMA = {
    "main_chat_id": Field(str, required=True),
    "additional_chat_ids": Field(list, default=None),
}


@bp.get("/preferences")
@require_auth(SCOPE_NOTIFICATIONS_READ)
def get_preferences():
    return ok(g.user.notification_preferences or {})


@bp.put("/preferences")
@require_auth(SCOPE_NOTIFICATIONS_WRITE)
def update_preferences():
    payload = validate(get_json(), _PREFS_SCHEMA)
    prefs = dict(g.user.notification_preferences or {})
    for key in _PREF_KEYS:
        if payload.get(key) is not None:
            prefs[key] = payload[key]
    g.user.notification_preferences = prefs
    db.session.commit()
    return ok(prefs)


@bp.get("/telegram")
@require_auth(SCOPE_NOTIFICATIONS_READ)
def telegram_status():
    return ok(_telegram_view(g.user))


@bp.post("/telegram/start-link")
@require_auth(SCOPE_NOTIFICATIONS_WRITE)
def telegram_start_link():
    """Begin the deep-link connect flow; the frontend opens *deep_link*."""
    instruction = TelegramConnector().start_link(g.user)
    return ok(
        {
            "deep_link": instruction.deep_link,
            "expires_at": instruction.expires_at.isoformat(),
            "instructions": instruction.instructions,
        }
    )


@bp.put("/telegram")
@require_auth(SCOPE_NOTIFICATIONS_WRITE)
def telegram_connect():
    """Legacy chat-id paste flow. Prefer the deep-link handshake instead."""
    payload = validate(get_json(), _TELEGRAM_SCHEMA)
    main = payload["main_chat_id"].strip()
    if not main.lstrip("-").isdigit():
        raise BadRequest("main_chat_id must be numeric", code="invalid_chat_id")

    additional = [
        str(c).strip()
        for c in (payload.get("additional_chat_ids") or [])
        if str(c).strip()
    ]
    g.user.telegram_chat_ids = {"main": main, "additional": additional}
    g.user.telegram_connected = True
    db.session.commit()
    return ok(_telegram_view(g.user))


@bp.delete("/telegram")
@require_auth(SCOPE_NOTIFICATIONS_WRITE)
def telegram_disconnect():
    TelegramConnector().disconnect(g.user)
    return ok(_telegram_view(g.user))


@bp.post("/telegram/test")
@require_auth(SCOPE_NOTIFICATIONS_WRITE)
def telegram_test():
    sent = NotificationManager.send_test_notification(g.user)
    return ok({"sent": bool(sent)})


def _telegram_view(user) -> dict:
    return {
        "connected": bool(user.telegram_connected),
        "chat_ids": user.telegram_chat_ids or {"main": None, "additional": []},
        "notifications_enabled": bool(user.telegram_notifications_enabled),
    }
