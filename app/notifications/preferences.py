from __future__ import annotations

from typing import Any


class NotificationPreferencePolicy:
    """Evaluate user-level notification settings."""

    def allows(self, user: Any, notification_type: str) -> bool:
        """Return whether a notification type is enabled for the user."""
        if not getattr(user, "telegram_notifications_enabled", True):
            return False

        preferences = getattr(user, "notification_preferences", None) or {}
        return bool(preferences.get(notification_type, True))
