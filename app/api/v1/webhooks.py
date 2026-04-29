"""External webhook receivers (no Bearer auth — verified by upstream signature)."""

from __future__ import annotations

import logging

import stripe
from flask import Blueprint, current_app, request

from app.api.errors import BadRequest
from app.api.responses import ok
from app.stripe.stripe_fulfillment import (
    handle_invoice_paid,
    handle_invoice_payment_failed,
    handle_new_subscription,
    handle_subscription_deleted,
    handle_subscription_updated,
)

bp = Blueprint("webhooks", __name__, url_prefix="/webhooks")

logger = logging.getLogger(__name__)

_STRIPE_HANDLERS = {
    "customer.subscription.created": handle_new_subscription,
    "customer.subscription.updated": handle_subscription_updated,
    "customer.subscription.deleted": handle_subscription_deleted,
    "invoice.paid": handle_invoice_paid,
    "invoice.payment_failed": handle_invoice_payment_failed,
}


@bp.post("/stripe")
def stripe_webhook():
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
    event = _parse_event()
    handler = _STRIPE_HANDLERS.get(event["type"])
    if handler is None:
        logger.info("Unhandled Stripe event: %s", event["type"])
        return ok({"received": True, "handled": False})

    handler(event)
    return ok({"received": True, "handled": True})


def _parse_event():
    payload = request.get_data()
    signature = request.headers.get("Stripe-Signature", "")
    secret = current_app.config["STRIPE_WEBHOOK_SECRET"]
    try:
        return stripe.Webhook.construct_event(payload, signature, secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise BadRequest(f"Invalid Stripe signature: {exc}", code="invalid_signature")
