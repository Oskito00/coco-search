"""API error types and JSON error envelope."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Raise from any handler to return a structured JSON error."""

    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, status: int | None = None, details: Any = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status is not None:
            self.status_code = status
        self.details = details


class BadRequest(ApiError):
    status_code = 400
    code = "bad_request"


class Unauthorized(ApiError):
    status_code = 401
    code = "unauthorized"


class Forbidden(ApiError):
    status_code = 403
    code = "forbidden"


class NotFound(ApiError):
    status_code = 404
    code = "not_found"


class Conflict(ApiError):
    status_code = 409
    code = "conflict"


class RateLimited(ApiError):
    status_code = 429
    code = "rate_limited"


def _envelope(message: str, code: str, status: int, details: Any = None):
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return jsonify(body), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def _handle_api_error(exc: ApiError):
        return _envelope(exc.message, exc.code, exc.status_code, exc.details)

    @app.errorhandler(HTTPException)
    def _handle_http(exc: HTTPException):
        return _envelope(exc.description or exc.name, exc.name.lower().replace(" ", "_"), exc.code or 500)

    @app.errorhandler(Exception)
    def _handle_unexpected(exc: Exception):
        logger.exception("Unhandled exception in API")
        return _envelope("Internal server error", "internal_error", 500)
