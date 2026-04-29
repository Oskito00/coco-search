"""Stripe subscription endpoints."""

from __future__ import annotations

import stripe
from flask import Blueprint, current_app, g

from app.api.errors import BadRequest
from app.api.middleware import require_auth
from app.api.responses import ok
from app.api.schemas import Field, get_json, validate
from app.auth import SCOPE_SUBSCRIPTION_WRITE
from app.stripe import subscription_service as service
from app.stripe.subscription_service import SubscriptionError

bp = Blueprint("subscription", __name__, url_prefix="/subscription")


@bp.before_request
def _configure_stripe():
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]


_CHECKOUT_SCHEMA = {
    "price_id": Field(str, required=True),
    "success_url": Field(str, required=True),
    "cancel_url": Field(str, required=True),
}

_PRICE_SCHEMA = {"price_id": Field(str, required=True)}

_PORTAL_SCHEMA = {"return_url": Field(str, required=True)}


@bp.post("/checkout")
@require_auth(SCOPE_SUBSCRIPTION_WRITE)
def create_checkout():
    payload = validate(get_json(), _CHECKOUT_SCHEMA)
    result = _run(
        service.create_checkout,
        g.user,
        payload["price_id"],
        payload["success_url"],
        payload["cancel_url"],
    )
    return ok({"url": result.url, "session_id": result.session_id})


@bp.post("/cancel")
@require_auth(SCOPE_SUBSCRIPTION_WRITE)
def cancel():
    _run(service.schedule_cancellation, g.user)
    return ok({"status": "pending_cancellation"})


@bp.post("/resume")
@require_auth(SCOPE_SUBSCRIPTION_WRITE)
def resume():
    _run(service.resume_subscription, g.user)
    return ok({"status": "active"})


@bp.post("/upgrade")
@require_auth(SCOPE_SUBSCRIPTION_WRITE)
def upgrade():
    payload = validate(get_json(), _PRICE_SCHEMA)
    _run(service.upgrade, g.user, payload["price_id"])
    return ok({"status": "upgraded"})


@bp.post("/downgrade")
@require_auth(SCOPE_SUBSCRIPTION_WRITE)
def downgrade():
    payload = validate(get_json(), _PRICE_SCHEMA)
    _run(service.schedule_downgrade, g.user, payload["price_id"])
    return ok({"status": "downgrade_scheduled"})


@bp.post("/cancel-downgrade")
@require_auth(SCOPE_SUBSCRIPTION_WRITE)
def cancel_downgrade():
    _run(service.cancel_scheduled_downgrade, g.user)
    return ok({"status": "downgrade_cancelled"})


@bp.post("/portal")
@require_auth(SCOPE_SUBSCRIPTION_WRITE)
def portal():
    payload = validate(get_json(), _PORTAL_SCHEMA)
    url = _run(service.create_portal_session, g.user, payload["return_url"])
    return ok({"url": url})


def _run(fn, *args):
    try:
        return fn(*args)
    except SubscriptionError as exc:
        raise BadRequest(str(exc), code="subscription_error")
