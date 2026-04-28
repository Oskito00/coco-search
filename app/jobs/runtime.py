from collections.abc import Callable
from typing import TypeVar

from app.extensions import db, scheduler

T = TypeVar("T")


def run_with_scheduler_context(work: Callable[[], T]) -> T | None:
    """Run scheduled work inside the Flask app context with session cleanup."""
    with scheduler.app.app_context():
        try:
            return work()
        except Exception as exc:
            db.session.rollback()
            print(f"Error: {exc}")
            return None
        finally:
            db.session.remove()
