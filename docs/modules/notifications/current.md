# `app/notifications/` — Current State

Pluggable notification pipeline: select events from a search result, filter
them by relevance + per-user preferences, render per-channel, deliver.

The core idea: **adding a new messaging surface (Telegram → WhatsApp →
Google Chat) is three new files and one dispatcher entry. The pipeline does
not change.**

## Pipeline

```
SearchProcessingResult
  └── SearchEventSelector ───▶ NotificationEvent (one per type)
            │
            ▼
      EventNotificationService.notify_search_events(query, result)
        │
        ├── UserNotificationRepository.get(user_id)
        ├── NotificationPreferencePolicy.allows(user, type)?    ─── skip if no
        ├── NotificationRelevanceFilter.relevant_payloads(...)  ─── prune list
        ├── NotificationRecordCreator.create_records(...)       ─── pending row
        ├── NotificationDispatcher.dispatch(user, event, payloads)
        │     │
        │     └── for each enabled channel:
        │           formatter.format(event, payloads) → RenderedMessage
        │           channel.send(user, rendered_message) → DeliveryResult
        │
        └── records.mark_sent(...) | records.mark_failed(...)
```

## Three composable layers

### 1. `channels/` — *delivery*

A `NotificationChannel` knows how to push a `RenderedMessage` to one user.
That is its entire responsibility — no rendering, no preference logic, no
account linking.

| Channel | File | Notes |
|---|---|---|
| `TelegramChannel` | `channels/telegram.py` | Iterates `user.telegram_chat_ids[main + additional]`, calls `https://api.telegram.org/bot<token>/sendMessage`. |
| `EmailChannel` | `channels/email.py` | Routes through `app.utils.email.send_email`. |

`channels/base.py` holds the `NotificationChannel` ABC + the
`RenderedMessage` and `DeliveryResult` dataclasses every channel consumes.

### 2. `formatters/` — *rendering*

A `NotificationFormatter` turns a `NotificationEvent` into a
channel-flavoured `RenderedMessage`.

| Formatter | File | Style |
|---|---|---|
| `TelegramFormatter` | `formatters/telegram.py` | HTML, emoji, 5-item preview for new-items, 5-batch for ending auctions. |
| `EmailFormatter` | `formatters/email.py` | HTML email, simple inline styling. |

Both formatters branch on `event.notification_type` (`new_items` /
`price_drops` / `auction_alerts`) — that's the only place those types are
inspected outside of `events.py`.

### 3. `connectors/` — *account linking*

A `MessagingConnector` owns the lifecycle of binding a user account to a
channel. The shape:

```python
connector.start_link(user)        -> LinkInstruction(deep_link, expires_at, instructions)
connector.is_connected(user)      -> bool
connector.disconnect(user)        -> None
# webhook-only, not on the ABC:
TelegramConnector.finish_link(token, chat_id) -> Optional[LinkOutcome]
```

#### Telegram zero-paste flow

1. Frontend hits `POST /api/v1/notifications/telegram/start-link`.
2. `TelegramConnector.start_link` mints a 10-minute itsdangerous token via
   `LinkTokenService` and returns
   `https://t.me/<TELEGRAM_BOT_USERNAME>?start=<token>`.
3. User taps **Start** in Telegram.
4. Telegram delivers an update to `POST /api/v1/webhooks/telegram` (signed
   with `TELEGRAM_WEBHOOK_SECRET` via the `X-Telegram-Bot-Api-Secret-Token`
   header).
5. `parse_start_command` strips the token from the `/start <token>` text.
6. `TelegramConnector.finish_link(token, chat_id)` verifies the token,
   stores `chat_id` on the user, sets `telegram_connected=True`, sends a
   confirmation message back through the channel.

The user pastes nothing.

`LinkTokenService` (in `connectors/tokens.py`) wraps
`itsdangerous.URLSafeTimedSerializer` with a per-kind salt so a Telegram
token can never be reused for a future WhatsApp / Google-Chat connector.

## `dispatch.py`

`NotificationDispatcher` holds a list of `ChannelBinding(channel, formatter)`
pairs. `dispatch(user, event, payloads)` skips any channel where
`channel.is_available(user)` is false, then formats + sends via the rest.
`default_bindings()` returns the production list (Telegram + email).

## `service.py`

`EventNotificationService` is the only public surface used by the rest of
the app. It composes:

- `UserNotificationRepository` (loads `User` rows)
- `SearchEventSelector` (`events.py`)
- `NotificationPreferencePolicy` (`preferences.py`)
- `NotificationRelevanceFilter` (`relevance.py`) — wraps the real
  `RelevanceService` from `app.relevance`
- `NotificationRecordCreator` (`records.py`)
- `NotificationDispatcher`

Each is injectable for tests.

## Backwards-compat shims

- `delivery.py` — re-exports `NotificationDispatcher` and aliases
  `RenderedMessage` as `RenderedNotification`. New code should import from
  `dispatch` / `channels` directly.
- `telegram.py` — `NotificationManager` retains a single static method
  (`send_test_notification`) that powers `POST /notifications/telegram/test`.
  All other helpers from the old god-class are gone.

## Current package layout

```text
app/notifications/
  __init__.py
  delivery.py                  (compat shim)
  dispatch.py                  (NotificationDispatcher)
  events.py                    (NotificationEvent, SearchEventSelector)
  preferences.py               (NotificationPreferencePolicy)
  records.py                   (NotificationRecordCreator)
  relevance.py                 (NotificationRelevanceFilter)
  service.py                   (EventNotificationService)
  telegram.py                  (compat shim — only send_test_notification)
  channels/
    __init__.py
    base.py                    (NotificationChannel ABC + dataclasses)
    email.py
    telegram.py
  formatters/
    __init__.py
    base.py                    (NotificationFormatter ABC)
    email.py
    telegram.py
  connectors/
    __init__.py
    base.py                    (MessagingConnector ABC + dataclasses)
    telegram.py                (start_link / finish_link / is_connected / disconnect)
    tokens.py                  (LinkTokenService — itsdangerous wrapper)
```

## Adding a new channel

1. Implement `NotificationChannel` in `channels/<name>.py`.
2. Implement `NotificationFormatter` in `formatters/<name>.py`.
3. Implement `MessagingConnector` in `connectors/<name>.py` (only if the
   channel needs an account-linking handshake).
4. Append the `(channel, formatter)` pair to `default_bindings()` in
   `dispatch.py`.
5. Add the connect-flow API in `app/api/v1/notifications.py` and the
   webhook (if any) in `app/api/v1/webhooks.py`.

No changes anywhere else.
