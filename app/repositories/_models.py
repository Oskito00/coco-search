"""Shared helpers for repository model access."""

from typing import Any, Optional, Type

from sqlalchemy import inspect

from app.extensions import db
from app import models


class RepositoryModelUnavailable(RuntimeError):
    """Raised when a repository depends on a model not present in this branch."""


def default_session() -> Any:
    """Return the default SQLAlchemy session used by repositories."""
    return db.session


def optional_model(model_name: str) -> Optional[Type[Any]]:
    """Return a model class if it exists on app.models."""
    return getattr(models, model_name, None)


def require_model(model: Optional[Type[Any]], model_name: str) -> Type[Any]:
    """Return a model class or raise a clear schema dependency error."""
    if model is None:
        message = (
            f"{model_name} model is not available. This repository method depends "
            "on the schema-worker model for that table."
        )
        raise RepositoryModelUnavailable(message)
    return model


def model_columns(model: Type[Any]) -> set[str]:
    """Return mapped column names for a SQLAlchemy model."""
    return {column.key for column in inspect(model).mapper.column_attrs}


def compact_values(values: dict[str, Any]) -> dict[str, Any]:
    """Drop unset values before constructing or updating models."""
    return {key: value for key, value in values.items() if value is not None}


def create_model(model: Type[Any], values: dict[str, Any]) -> Any:
    """Create a model instance from values that match mapped columns."""
    columns = model_columns(model)
    return model(
        **{
            key: value
            for key, value in compact_values(values).items()
            if key in columns
        }
    )


def update_model(instance: Any, values: dict[str, Any]) -> bool:
    """Update mapped attributes on an instance and report whether anything changed."""
    changed = False
    columns = model_columns(type(instance))
    for key, value in compact_values(values).items():
        if key in columns and getattr(instance, key) != value:
            setattr(instance, key, value)
            changed = True
    return changed
