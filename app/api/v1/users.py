"""Authenticated user profile endpoints."""

from __future__ import annotations

from flask import Blueprint, g

from app.api.middleware import require_auth
from app.api.responses import ok
from app.auth import SCOPE_USER_READ
from app.models import User

bp = Blueprint("users", __name__, url_prefix="/me")


@bp.get("")
@require_auth(SCOPE_USER_READ)
def get_me():
    return ok(_user_view(g.user))


def _user_view(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "email_verified": user.email_verified,
        "telegram_connected": user.telegram_connected,
        "telegram_notifications_enabled": user.telegram_notifications_enabled,
        "notification_preferences": user.notification_preferences,
        "tier": user.tier,
        "subscription_status": user.subscription_status,
        "query_usage": user.query_usage,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
