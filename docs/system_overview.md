# Coco Search — System Overview

This document walks the full lifecycle of a search: from a logged-in user submitting a form, through scheduling, eBay calls, item processing, and notification delivery. It also flags the gaps where wiring exists but the default code path short-circuits the feature.

Read this top-to-bottom once. After that, the **End-to-End Walkthrough** and **What's Live vs Stubbed** sections are the working references.

---

## 1. Product

Coco Search is a multi-tenant eBay notifier. A user defines a **saved search** (keywords + filters + cadence) and the system polls eBay on their behalf, deduplicates results, and pushes notifications (Telegram + email) for new matches, price drops, and auctions ending soon.

The long-term direction is an agentic backend: an iOS / chat client where the user only states intent, and agents handle search creation, refinement, and feedback. The current codebase is the deterministic plumbing underneath that vision.

---

## 2. Tech Stack

- **Web framework**: Flask (app factory in [app/__init__.py](app/__init__.py))
- **ORM**: SQLAlchemy + Alembic migrations (`migrations/`)
- **Database**: PostgreSQL (JSONB columns used heavily for `telegram_chat_ids`, `notification_preferences`, `tier`)
- **Auth**: Flask-Login (server-side sessions, cookie-based)
- **Forms / CSRF**: Flask-WTF + WTForms
- **Security headers**: Flask-Talisman; **Rate limiting**: Flask-Limiter
- **Email**: Flask-Mail (SMTP)
- **Background jobs**: APScheduler with a SQLAlchemy job store (jobs persist across restarts)
- **eBay SDK**: standalone `ebay_client/` package (OAuth + Browse API + Analytics)
- **Billing**: Stripe (webhooks at [app/routes/stripe_webhook.py](app/routes/stripe_webhook.py))
- **Telegram**: direct HTTPS calls via `requests` from [app/notifications/telegram.py](app/notifications/telegram.py)

There is **no JSON API surface**. Every entry point is an HTML route guarded by a session cookie.

---

## 3. Authentication & User Scoping

### How a user signs in

Defined in [app/routes/auth.py](app/routes/auth.py). Flask-Login session cookies; passwords hashed with werkzeug; email confirmation and password reset use itsdangerous time-bound tokens emailed via Flask-Mail.

### How a request is scoped to a user

Every protected route uses `@login_required`, which makes `flask_login.current_user` available. All search routes pull `current_user.id` and store it as `UserQuery.user_id`. Database reads are filtered by that user ID — there is no row-level security in Postgres; isolation is enforced application-side.

### What's *not* there

- No API tokens / JWT / OAuth-for-third-parties.
- No admin role separation in code (a few routes check `current_user.is_admin` but tooling around it is thin).
- No per-request tenant header — sessions only.

This matters for the agentic future: an iOS app or external agent will need a real API surface (token-based auth, JSON endpoints). Today the only programmatic surfaces are the Stripe webhook and the eBay outbound client.

---

## 4. Domain Model (the tables that matter)

All in [app/models.py](app/models.py). Grouped by purpose:

**Identity & billing**
- `User` — Flask-Login `UserMixin`. Holds `email`, `password_hash`, `confirmed`, `telegram_connected`, `telegram_chat_ids` (JSONB: `{main, additional[]}`), `notification_preferences` (JSONB), `tier` (JSONB plan/limits), Stripe customer/subscription IDs.

**Search definitions**
- `UserQuery` — one row per saved search. UUID `query_id`, FKs to `User` and `Keyword`, plus filter columns (`min_price`, `max_price`, `condition`, `marketplace`, `item_location`, `buying_options`, `required_keywords`, `excluded_keywords`), schedule columns (`check_interval` minutes, default 5; `is_active`; `first_run`; `last_full_run`/`next_full_run`; `last_recent_run`).
- `Keyword` — deduped phrases shared across users (`keyword_text` unique).
- `KeywordItems` — many-to-many bridge between keywords and items.

**Items & observations**
- `Item` — global eBay item, deduped by `ebay_id`. Snapshot of price, currency, URL, condition, seller, location, end-time, etc.
- `UserQueryItems` — links a `UserQuery` to an `Item` it has matched, with flags like `auction_ending_notification_sent`.
- `ItemObservation` — append-only log of observed price/state per item per run. **Schema exists; not written by the default code path** (see §10).
- `ItemFeatureSnapshot` — feature vectors used by the relevance layer.

**Relevance & feedback**
- `UserItemInteraction` — explicit interactions (clicked, dismissed, purchased, etc).
- `ItemRelevanceFeedback` — legacy thumbs-up/down feedback.

**Events & notifications**
- `DomainEvent` — outbox pattern (new item, price drop, auction ending). **Schema exists; not written by the default code path** (see §10).
- `NotificationRecord` — what was sent, to whom, via which channel. **Not written by the default code path** (see §10).

**Operational**
- `SearchRun` — one row per scrape attempt with timing/outcome. **Not written by default** (see §10).

---

## 5. Search Creation Flow

### What the user submits

`QueryForm` in [app/forms.py](app/forms.py):

| Field | Notes |
|---|---|
| `keywords` | Required. Free text. |
| `min_price` / `max_price` | Optional numeric. |
| `check_interval` | Minutes between recent-scrape jobs. **Min 5, max 120.** Default 5. |
| `required_keywords` / `excluded_keywords` | Hard filters applied post-scrape. |
| `marketplace` | Default `EBAY_GB`. |
| `item_location` | Default `any`. |
| `condition` | `''` / `NEW` / `USED`. |
| `buying_options` | `FIXED_PRICE\|AUCTION` / `FIXED_PRICE` / `AUCTION`. |

### Route → service

`POST /queries/create` (or similar) in [app/routes/queries.py](app/routes/queries.py) calls `_create_saved_search` (around line 223), which:

1. **Quota check** against `current_user.tier`.
2. **Resolve `Keyword`** (find-or-create on `keyword_text`).
3. **Duplicate check** — same user + same keyword + same filters → reject.
4. **INSERT `UserQuery`** with `is_active=True`, `first_run=True`.
5. **`_load_historical_items`** — backfills `UserQueryItems` from already-stored `Item` rows that match the filters. **No eBay call happens here.**
6. Commit and redirect.

The HTTP request returns *without ever calling eBay*. The actual scraping starts on the next scheduler tick (see §6).

---

## 6. Scheduling

The scheduler is APScheduler embedded in the Flask process, using a SQLAlchemy job store (config in [config.py](config.py)). Jobs survive process restarts.

### Three kinds of jobs per query

`add_query_jobs(query_id)` in [app/_scheduler/job_manager.py](app/_scheduler/job_manager.py) registers two jobs per active query:

- **`query_<id>_full`** — runs every **24 hours**, with the *first run executed immediately*. Intended as the heavy "rebaseline" pass.
- **`query_<id>_recent`** — runs every `check_interval` minutes (≥5). Intended as the cheap "have any new items appeared?" pass.

### Reconciliation loop

A third, global job runs every **60 seconds**: `sync_jobs` in [app/jobs/snyc_jobs.py](app/jobs/snyc_jobs.py) (note typo in filename). It calls `ScheduledJobSynchronizer().sync()`, which:

- Walks every `UserQuery` where `is_active=True`.
- Ensures both APScheduler jobs exist for it. If not, calls `add_query_jobs`.
- Removes APScheduler jobs whose query was deactivated/deleted.

**This is why the create-search route doesn't have to register jobs itself.** The next sync tick (≤60s away) will pick the new query up. The trade-off is a worst-case 60-second delay between creating a search and the first eBay call.

### Why two cadences

The user designed this against the eBay rate limit (~5000 calls/day per credential). Recent scrapes paginate just enough to detect new items; full scrapes refresh the whole result set. **Caveat**: today both cadences call the same eBay function with the same parameters (see §7) — the *intent* is good, the *implementation* doesn't realize the savings yet.

---

## 7. eBay Execution

[app/searches/execution.py](app/searches/execution.py) contains `scrape_ebay` and `scrape_new_items` (lines 64–94). **They are byte-identical right now** — both call `ebay_client.api.search_items(keywords, filters, sort_order, max_pages, marketplace)`. Refactoring `scrape_new_items` to a smaller `max_pages` + `EndingSoonest`/`NewlyListed` sort is the obvious next optimization.

`ebay_client/` is independent of Flask. It owns OAuth tokens, Browse search calls, and rate-limit checks. Nothing in `ebay_client/` imports from `app/`.

A simple **circuit breaker** (threshold 3 failures, 60s recovery) wraps the outbound calls.

---

## 8. Item Processing

[app/searches/item_processor.py](app/searches/item_processor.py) defines `SearchItemProcessor`. `process()` is called by the scheduled job with the list of raw items returned from eBay. For each item it:

1. Applies **hard filters** (`required_keywords`, `excluded_keywords`, price bounds the SDK didn't enforce).
2. **Upserts `Item`** (find-or-create by `ebay_id`).
3. **Links `UserQueryItems`** (skips if the link already exists).
4. **Suppresses notifications on first run** — `UserQuery.first_run=True` means we silently baseline; only after that do new items become notification-worthy.
5. Calls the notification service for items that pass relevance.

### ⚠️ Default-constructor short-circuits (lines 75–77)

```python
self.notifications = notification_service or EventNotificationService()
self.events = event_repository or self.items
self.observations = observation_repository or self.items
```

`ItemRepository` (used as the default `events` and `observations` repository) has neither `create()` for `DomainEvent` nor `create()` for `ItemObservation`. The persistence helpers `_persist_domain_event` / `_persist_observation` try `repository.create(...)` then fall back to optional `record_domain_event` / `record_observation` hooks — neither exists on `ItemRepository`.

**Net effect:** unless a caller explicitly injects a `DomainEventRepository` and an `ItemObservationRepository`, the `domain_events` and `item_observations` tables are never written to. Schema and classes are in place; the wiring is not.

---

## 9. Notifications

[app/notifications/service.py](app/notifications/service.py) `EventNotificationService` orchestrates: relevance check → channel dispatch → record.

- **Channels**: Telegram via [app/notifications/telegram.py](app/notifications/telegram.py) (HTTPS to `api.telegram.org`); email via [app/utils/email.py](app/utils/email.py) (Flask-Mail).
- **Per-user routing**: `User.telegram_chat_ids` JSONB holds `{main, additional}`; `User.notification_preferences` controls which event types go to which channel.
- **Test endpoint**: `/telegram/send_test_notification` ([app/routes/telegram.py:50](app/routes/telegram.py:50)) for manual verification.

### ⚠️ Two more default-constructor short-circuits

[app/notifications/relevance.py:64](app/notifications/relevance.py:64):
```python
self.relevance_service = relevance_service or AllowAllRelevanceService()
```
The real `RelevanceService` (with hard filters, feedback overrides, baseline scorer) lives in [app/relevance/service.py](app/relevance/service.py) but is **not wired into the live notification path**. Today every item that reaches the notification stage is allowed through.

[app/notifications/records.py:22](app/notifications/records.py:22):
```python
if self.repository is None:
    return 0
```
`NotificationRecordCreator` defaults to `repository=None`, so the `notification_records` table is never written. We have *no* persisted history of what was sent.

---

## 10. Relevance Layer

[app/relevance/service.py](app/relevance/service.py) defines `RelevanceService.should_notify(user, item, query)`:

1. Hard filters (price/condition/keywords).
2. Explicit feedback override (`ItemRelevanceFeedback` thumbs-down → suppress).
3. `BaselineRelevanceScorer` (heuristic; placeholder for a future model).

The intended training signals are `UserItemInteraction` rows (clicked, dismissed, purchased, etc.) and `ItemFeatureSnapshot` features. None of this is on the live path yet — see §9.

`SearchOnboardingService` exists for the "show 20 diverse items, ask which the user would buy" preview flow but **no route exposes it**. Onboarding is dead code waiting for a UI.

---

## 11. End-to-End Walkthrough

```
[Browser]
   │ session cookie (Flask-Login)
   ▼
POST /queries/create  ─── app/routes/queries.py::_create_saved_search
   │   • quota check
   │   • find-or-create Keyword
   │   • duplicate check
   │   • INSERT UserQuery (first_run=True, is_active=True)
   │   • _load_historical_items  ◄── no eBay call
   ▼
DB commit, HTTP redirect.

… up to 60s later …

APScheduler tick → sync_jobs every 60s
   │ ScheduledJobSynchronizer.sync()
   │   • finds UserQuery with no jobs
   │   • add_query_jobs(query_id)
   ▼
Two jobs registered:
   query_<id>_full    (24h, fires immediately)
   query_<id>_recent  (every check_interval min)

Job fires → ScheduledQueryService.run_query()
   │ scrape_ebay() → ebay_client.api.search_items()
   ▼
SearchItemProcessor.process(items)
   │ hard filters → upsert Item → link UserQueryItems
   │ if first_run: suppress notifications, then first_run = False
   │ ⚠ DomainEvent NOT persisted (default repo lacks create())
   │ ⚠ ItemObservation NOT persisted (same)
   ▼
EventNotificationService.notify(...)
   │ ⚠ AllowAllRelevanceService → everything allowed
   │ Telegram send (real) + Email send (real)
   │ ⚠ NotificationRecordCreator → no-op (repository=None)
   ▼
[User's Telegram / inbox]
```

---

## 12. What's Live vs Stubbed

| Capability | State |
|---|---|
| User signup / login / email confirm / password reset | **Live** |
| Stripe webhook for billing | **Live** |
| Telegram connect + send | **Live** |
| Search creation form + DB persistence | **Live** |
| Historical-item backfill on create | **Live** |
| APScheduler 60s reconciliation loop | **Live** |
| Full + recent scrape jobs registered per query | **Live** |
| eBay Browse search via `ebay_client/` | **Live** |
| Item dedupe + UserQueryItems linking | **Live** |
| First-run suppression | **Live** |
| Telegram + email delivery | **Live** |
| `recent_scrape` actually being lighter than `full_scrape` | **Stubbed** (identical functions) |
| `DomainEvent` persistence | **Stubbed** (default repo missing `create`) |
| `ItemObservation` persistence | **Stubbed** (same) |
| `SearchRun` persistence | **Stubbed** (`run_recorder=None` default) |
| `NotificationRecord` persistence | **Stubbed** (`repository=None` default) |
| `RelevanceService` on live path | **Stubbed** (`AllowAllRelevanceService` default) |
| `SearchOnboardingService` preview flow | **Built but unrouted** |
| JSON API for an iOS / agent client | **Not started** |
| Admin tooling | **Minimal** |

---

## 13. Codebase Map

```
app/
  __init__.py            Flask factory; registers blueprints + sync_jobs
  models.py              All SQLAlchemy models
  forms.py               WTForms (incl. QueryForm)
  extensions.py          db, login_manager, mail, csrf, scheduler, encryptor

  routes/
    auth.py              register/login/confirm/reset
    queries.py           create / list / edit / delete saved searches
    telegram.py          connect chat IDs, test notification
    settings.py
    subscription.py / stripe_webhook.py
    main.py / contact_feedback.py / legal.py

  searches/
    mapping.py           UserQuery <-> SavedSearch dataclasses
    execution.py         scrape_ebay / scrape_new_items
    item_processor.py    SearchItemProcessor (the hot path)
    scheduled.py         ScheduledQueryService (called by APScheduler)
    onboarding.py        SearchOnboardingService (unrouted)

  _scheduler/
    job_manager.py       add_query_jobs / remove_query_jobs
    synchronizer.py      reconciliation logic

  jobs/
    snyc_jobs.py         the 60s reconciliation tick (typo intentional in filename)

  notifications/
    service.py           EventNotificationService
    telegram.py          Telegram HTTP client
    relevance.py         NotificationRelevanceFilter (defaults to AllowAll)
    records.py           NotificationRecordCreator (no-op by default)

  relevance/
    service.py           RelevanceService + BaselineRelevanceScorer
    features.py          (skeleton) feature extraction

  repositories/
    items.py             ItemRepository
    …                    one wrapper per aggregate

  utils/
    email.py             Flask-Mail helpers

ebay_client/              Standalone eBay SDK (no Flask imports)
migrations/               Alembic
config.py                 DevelopmentConfig / ProductionConfig
```

---

## 14. Practical Mental Model

When you sit down to change something, hold these four ideas:

1. **The HTTP layer never calls eBay.** It writes a row and returns. Anything observable to the user happens on the scheduler.
2. **The 60-second sync loop is the load-bearing piece.** If it stops, no new searches start running. If it runs twice, you get duplicate jobs (the synchronizer is idempotent — verify this when refactoring).
3. **Default constructor arguments are silently disabling four whole features** (events, observations, runs, notification records, real relevance). When you want to turn one on, you wire a real repository / service into the constructor — you don't write new code.
4. **There is no API.** Everything assumes a session cookie. The agentic / iOS direction needs a parallel JSON surface; it's not a refactor of existing routes.
