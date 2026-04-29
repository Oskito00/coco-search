# `app/api/` — Current State

JSON-only HTTP surface. Every route is bearer-token authenticated except
the webhook receivers, which verify upstream signatures instead.

## Composition

`api/factory.py::register_api(app)` is the single entry point used by
`app.create_app`. It:

1. Calls `install_request_context(app)` from `api/middleware.py` — adds the
   per-request `g.user` / `g.token` plumbing.
2. Calls `register_error_handlers(app)` from `api/errors.py` — turns
   `ApiError`, `BadRequest`, `Forbidden`, etc. into a uniform JSON envelope.
3. Registers every blueprint listed in `api/v1/__init__.py::V1_BLUEPRINTS`
   under `/api/v1/...`.

## Shared infrastructure

| File | Purpose |
|---|---|
| `errors.py` | `ApiError` + subclasses; uniform `{"error": {...}}` JSON envelope. |
| `middleware.py` | `require_auth(scope)` decorator, `g.user` / `g.token` setup. |
| `responses.py` | `ok(payload)`, `created(payload)` helpers. |
| `schemas.py` | `Field`, `validate(get_json(), schema)` — small, dependency-free request validator. |
| `factory.py` | Wires everything onto the Flask app. |

## v1 blueprints

```
v1/auth_routes.py        POST /auth/login, /signup, /confirm, /password/reset, ...
v1/health.py             GET  /health
v1/items.py              GET  /items, /items/<id>
v1/notifications.py      GET/PUT /notifications/preferences
                         GET/PUT/DELETE /notifications/telegram
                         POST /notifications/telegram/start-link  (deep-link mint)
                         POST /notifications/telegram/test
v1/searches.py           CRUD on saved searches
v1/subscription.py       Stripe checkout / portal flows
v1/users.py              GET /users/me
v1/webhooks.py           POST /webhooks/stripe
                         POST /webhooks/telegram (deep-link finish)
```

## Telegram webhook

`v1/webhooks.py::telegram_webhook` is the back half of the zero-paste
connect flow described in `docs/modules/notifications/current.md`.

- Authenticated by the `X-Telegram-Bot-Api-Secret-Token` header (compared
  against `TELEGRAM_WEBHOOK_SECRET`). When the secret is unset, no
  verification runs.
- Extracts the linking token via
  `app.notifications.connectors.parse_start_command(text)` from a Telegram
  `/start <token>` update.
- Calls `TelegramConnector.finish_link(token, chat_id)` to persist the
  binding and send the confirmation message.

## Current package layout

```text
app/api/
  __init__.py
  errors.py
  factory.py
  middleware.py
  responses.py
  schemas.py
  v1/
    __init__.py
    auth_routes.py
    health.py
    items.py
    notifications.py
    searches.py
    subscription.py
    users.py
    webhooks.py
```
