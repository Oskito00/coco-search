# `app/billing/` + `app/stripe/` — Current State

Two thin packages cover the billing surface. The split exists for clarity:

- `app/billing/` — *plan/quota constants and policy* (no Stripe imports).
- `app/stripe/` — *Stripe SDK calls + webhook fulfillment* (imports
  `stripe`).

`app.api.v1.subscription` is the HTTP surface that consumes both.

## `app/billing/`

`constants.py` defines the plan tiers, their per-tier search quotas, and
human-readable labels. The rest of the app reads quotas via these
constants — never via a Stripe price id.

The package is intentionally tiny and import-clean so it can be consumed by
quota checks deep in the search-creation path without dragging Stripe along.

## `app/stripe/`

| File | Purpose |
|---|---|
| `subscription_service.py` | Creates Stripe Customers, subscriptions, and Customer Portal sessions. Used by `POST /subscription/checkout` etc. |
| `stripe_fulfillment.py` | Webhook handlers — one function per relevant Stripe event type. Updates `User.tier` / `User.stripe_subscription_id` based on the event. |

Webhook routing lives in `app/api/v1/webhooks.py`; the `_STRIPE_HANDLERS`
table dispatches each event type to the right `handle_*` function.

## Webhook events handled

```
customer.subscription.created   -> handle_new_subscription
customer.subscription.updated   -> handle_subscription_updated
customer.subscription.deleted   -> handle_subscription_deleted
invoice.paid                    -> handle_invoice_paid
invoice.payment_failed          -> handle_invoice_payment_failed
```

Anything else falls through with `handled: false`.

## Configuration

Set in `config.py`:

- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_INDIVIDUAL`, `STRIPE_PRICE_BUSINESS`, `STRIPE_PRICE_PRO`

## Current package layout

```text
app/billing/
  __init__.py
  constants.py           (plan tiers + quotas)

app/stripe/
  stripe_fulfillment.py  (webhook handlers)
  subscription_service.py (checkout / customer portal flows)
```
