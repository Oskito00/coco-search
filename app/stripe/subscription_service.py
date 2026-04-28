"""Stripe subscription operations. Pure-data inputs/outputs; no Flask request coupling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import stripe

from app.extensions import db
from app.models import User
from app.stripe.stripe_fulfillment import get_price_id_from_tier, get_tier_from_price


class SubscriptionError(Exception):
    """Wraps Stripe errors with a user-facing message."""


@dataclass(frozen=True)
class CheckoutResult:
    url: str
    session_id: str


def create_checkout(user: User, price_id: str, success_url: str, cancel_url: str) -> CheckoutResult:
    customer_id = _ensure_customer(user)
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            allow_promotion_codes=True,
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except stripe.error.StripeError as exc:
        raise SubscriptionError(str(exc))

    user.last_checkout_session_id = session.id
    db.session.commit()
    return CheckoutResult(url=session.url, session_id=session.id)


def schedule_cancellation(user: User) -> None:
    sub = _active_subscription_or_raise(user)
    _modify(sub.id, cancel_at_period_end=True)
    user.cancellation_requested = True
    user.subscription_status = "pending_cancellation"
    db.session.commit()


def resume_subscription(user: User) -> None:
    sub = _active_subscription_or_raise(user)
    _modify(sub.id, cancel_at_period_end=False)
    user.cancellation_requested = False
    user.subscription_status = "active"
    db.session.commit()


def upgrade(user: User, new_price_id: str) -> None:
    sub = _active_subscription_or_raise(user)
    item_id = _first_item_id(sub.id)
    _modify(
        sub.id,
        items=[{"id": item_id, "price": new_price_id}],
        proration_behavior="always_invoice",
    )
    user.tier = get_tier_from_price(new_price_id)
    db.session.commit()


def schedule_downgrade(user: User, new_price_id: str) -> None:
    sub = _active_subscription_or_raise(user)
    item_id = _first_item_id(sub.id)
    _modify(
        sub.id,
        items=[{"id": item_id, "price": new_price_id}],
        billing_cycle_anchor="unchanged",
        proration_behavior="none",
    )
    user.pending_tier = get_tier_from_price(new_price_id)
    user.pending_effective_date = datetime.fromtimestamp(sub.current_period_end)
    db.session.commit()


def cancel_scheduled_downgrade(user: User) -> None:
    sub = _active_subscription_or_raise(user)
    item_id = _first_item_id(sub.id)
    _modify(
        sub.id,
        cancel_at_period_end=False,
        items=[{"id": item_id, "price": get_price_id_from_tier(user.tier["name"])}],
        metadata={"cancel_downgrade": True},
    )
    user.pending_tier = None
    user.pending_effective_date = None
    db.session.commit()


def create_portal_session(user: User, return_url: str) -> str:
    if not user.stripe_customer_id:
        raise SubscriptionError("No Stripe customer for this user")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url,
    )
    return session.url


def _ensure_customer(user: User) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
    user.stripe_customer_id = customer.id
    db.session.commit()
    return customer.id


def _active_subscription_or_raise(user: User):
    if not user.stripe_customer_id:
        raise SubscriptionError("No Stripe customer for this user")
    subs = stripe.Subscription.list(customer=user.stripe_customer_id, status="active").data
    if not subs:
        raise SubscriptionError("No active subscription")
    return subs[0]


def _first_item_id(subscription_id: str) -> str:
    items = stripe.SubscriptionItem.list(subscription=subscription_id, limit=1)
    return items.data[0].id


def _modify(subscription_id: str, **kwargs) -> None:
    try:
        stripe.Subscription.modify(subscription_id, **kwargs)
    except stripe.error.StripeError as exc:
        raise SubscriptionError(str(exc))
