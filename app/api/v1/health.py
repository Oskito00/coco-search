"""Liveness + readiness endpoints for orchestrators."""

from flask import Blueprint
from sqlalchemy import text

from app.api.responses import ok
from app.extensions import db

bp = Blueprint("health", __name__, url_prefix="")


@bp.get("/healthz")
def healthz():
    return ok({"status": "ok"})


@bp.get("/readyz")
def readyz():
    db.session.execute(text("SELECT 1"))
    return ok({"status": "ready"})
