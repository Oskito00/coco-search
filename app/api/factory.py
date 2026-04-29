"""Wires v1 blueprints + middleware + error handlers onto a Flask app."""

from __future__ import annotations

from flask import Flask

from app.api.errors import register_error_handlers
from app.api.middleware import install_request_context
from app.api.v1 import V1_BLUEPRINTS, V1_PREFIX


def register_api(app: Flask) -> None:
    install_request_context(app)
    register_error_handlers(app)
    for bp in V1_BLUEPRINTS:
        app.register_blueprint(bp, url_prefix=f"{V1_PREFIX}{bp.url_prefix or ''}")
