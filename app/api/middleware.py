"""Bearer-auth decorator + per-request context helpers."""

from __future__ import annotations

import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, g, request

from app.api.errors import Forbidden, Unauthorized
from app.auth.tokens import verify_token
from app.extensions import db


def install_request_context(app: Flask) -> None:
    @app.before_request
    def _attach_request_id():
        g.request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex

    @app.after_request
    def _emit_request_id(response):
        response.headers["X-Request-Id"] = g.get("request_id", "")
        return response


def require_auth(*required_scopes: str):
    """Decorator: enforce Bearer token + optional scopes. Sets g.user, g.token."""

    def wrapper(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            token = _bearer_token_from_request()
            if not token:
                raise Unauthorized("Missing bearer token", code="missing_token")

            record = verify_token(token)
            if record is None:
                raise Unauthorized("Invalid or expired token", code="invalid_token")

            if not _has_scopes(record.scopes, required_scopes):
                raise Forbidden(
                    f"Token lacks required scopes: {list(required_scopes)}",
                    code="insufficient_scope",
                )

            g.token = record
            g.user = record.user
            record.last_used_at = datetime.utcnow()
            db.session.flush()
            return fn(*args, **kwargs)

        return inner

    return wrapper


def _bearer_token_from_request() -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    return header.split(" ", 1)[1].strip() or None


def _has_scopes(token_scopes, required_scopes) -> bool:
    if not required_scopes:
        return True
    granted = set(token_scopes or [])
    if "admin" in granted:
        return True
    return set(required_scopes).issubset(granted)
