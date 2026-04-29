"""App-context wrapper for RQ jobs. Workers reuse a single Flask app per process."""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import Flask

_app: Flask | None = None


def get_worker_app() -> Flask:
    global _app
    if _app is None:
        from app import create_app
        _app = create_app()
    return _app


def with_app_context(fn: Callable) -> Callable:
    @wraps(fn)
    def inner(*args, **kwargs):
        with get_worker_app().app_context():
            return fn(*args, **kwargs)

    return inner
