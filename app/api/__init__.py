"""API package: JSON-only Flask blueprints under /api/v1."""

from app.api.factory import register_api

__all__ = ["register_api"]
