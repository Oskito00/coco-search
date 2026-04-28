"""Tiny helpers for consistent JSON responses."""

from __future__ import annotations

from typing import Any

from flask import jsonify


def ok(data: Any = None, status: int = 200):
    return jsonify({"data": data}), status


def created(data: Any = None):
    return ok(data, status=201)


def no_content():
    return ("", 204)


def paginated(items: list, page: int, per_page: int, total: int):
    return ok(
        {
            "items": items,
            "page": page,
            "per_page": per_page,
            "total": total,
        }
    )
