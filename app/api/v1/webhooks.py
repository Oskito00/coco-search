"""External webhook receivers (no Bearer auth — verified by upstream signature)."""

from __future__ import annotations

import logging

import stripe
from flask import Blueprint, current_app, request

from app.api.errors import BadRequest
from app.api.responses import ok
from app.notifications.connectors import TelegramConnector, parse_start_command
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


# ----------------------------------------------------------------- Telegram


@bp.post("/telegram")
def telegram_webhook():
    """Complete the Telegram deep-link handshake from a ``/start <token>`` update.

    Authenticated by a shared secret in ``TELEGRAM_WEBHOOK_SECRET`` (compared
    against the ``X-Telegram-Bot-Api-Secret-Token`` header that Telegram sends
    when the webhook is registered with that secret).
    """
    _verify_telegram_signature()
    update = request.get_json(silent=True) or {}
    binding = _telegram_binding_from_update(update)
    if binding is None:
        return ok({"received": True, "handled": False})

    token, chat_id = binding
    outcome = TelegramConnector().finish_link(token, chat_id)
    if outcome is None:
        logger.info("Telegram webhook received an invalid or expired link token")
        return ok({"received": True, "handled": False})

    return ok(
        {
            "received": True,
            "handled": True,
            "user_id": outcome.user_id,
            "delivered_confirmation": outcome.delivered_confirmation,
        }
    )


def _verify_telegram_signature() -> None:
    expected = current_app.config.get("TELEGRAM_WEBHOOK_SECRET")
    if not expected:
        return  # Webhook configured without a secret; skip verification.
    provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if provided != expected:
        raise BadRequest("Invalid Telegram signature", code="invalid_signature")


def _telegram_binding_from_update(update: dict) -> tuple[str, str] | None:
    """Extract ``(token, chat_id)`` from a Telegram update, or None."""
    message = update.get("message") or update.get("edited_message") or {}
    token = parse_start_command(message.get("text"))
    chat_id = (message.get("chat") or {}).get("id")
    if token is None or chat_id is None:
        return None
    return token, str(chat_id)
