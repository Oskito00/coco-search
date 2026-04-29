"""Tiny request-body validator. Avoids pulling in pydantic for low complexity."""

from __future__ import annotations

from typing import Any, Callable

from flask import request

from app.api.errors import BadRequest


class Field:
    __slots__ = ("type", "required", "default", "choices", "min", "max", "validator")

    def __init__(
        self,
        type: type | tuple[type, ...] = str,
        required: bool = False,
        default: Any = None,
        choices: list | None = None,
        min: float | int | None = None,
        max: float | int | None = None,
        validator: Callable[[Any], Any] | None = None,
    ):
        self.type = type
        self.required = required
        self.default = default
        self.choices = choices
        self.min = min
        self.max = max
        self.validator = validator


def get_json() -> dict:
    payload = request.get_json(silent=True)
    if payload is None:
        raise BadRequest("Request body must be JSON", code="invalid_json")
    if not isinstance(payload, dict):
        raise BadRequest("JSON body must be an object", code="invalid_json")
    return payload


def validate(payload: dict, schema: dict[str, Field]) -> dict:
    """Apply a flat schema to a JSON payload, returning a clean dict."""
    cleaned: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for name, field in schema.items():
        if name not in payload:
            if field.required:
                errors[name] = "required"
                continue
            cleaned[name] = field.default
            continue

        value = payload[name]
        problem = _check_field(value, field)
        if problem:
            errors[name] = problem
            continue
        cleaned[name] = value

    if errors:
        raise BadRequest("Validation failed", code="validation_failed", details=errors)
    return cleaned


def _check_field(value: Any, field: Field) -> str | None:
    if value is None and not field.required:
        return None
    if not isinstance(value, field.type):
        return f"must be {_type_name(field.type)}"
    if field.choices is not None and value not in field.choices:
        return f"must be one of {field.choices}"
    if field.min is not None and value < field.min:
        return f"must be >= {field.min}"
    if field.max is not None and value > field.max:
        return f"must be <= {field.max}"
    if field.validator is not None:
        try:
            field.validator(value)
        except ValueError as exc:
            return str(exc)
    return None


def _type_name(t):
    if isinstance(t, tuple):
        return " or ".join(x.__name__ for x in t)
    return t.__name__
