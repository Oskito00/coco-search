"""Deprecated module — kept only for import-path stability during the cutover.

All delivery flows now live in :mod:`app.notifications.dispatch`. This file
re-exports a couple of names so any straggler imports keep working until the
next cleanup pass; new code should import directly from ``dispatch`` /
``channels`` / ``formatters``.
"""

from __future__ import annotations

from app.notifications.channels import RenderedMessage as RenderedNotification
from app.notifications.dispatch import NotificationDispatcher

__all__ = ["NotificationDispatcher", "RenderedNotification"]
