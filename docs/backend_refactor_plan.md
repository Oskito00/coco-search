# Backend Refactor Plan

This repo is moving toward a backend-first modular structure for an eBay notifier SaaS.

## Current seams

- `app/ebay/api.py` remains the compatibility import for existing code and tests.
- Pure eBay API code now lives in `app/ebay/auth.py`, `app/ebay/client.py`, `app/ebay/dto.py`, `app/ebay/parsers.py`, and `app/ebay/config.py`.
- Search execution and item processing are separated under `app/searches/`.
- SQLAlchemy access starts moving behind `app/repositories/`.
- Notification event dispatch starts moving behind `app/notifications/`.
- Feedback and baseline relevance scoring start moving behind `app/relevance/`.
- Stripe stays under `app/stripe/` for now. `app/billing/` is only a package boundary placeholder.

## Near-term target

1. Keep `app/models.py` as the schema source while moving query, item, feedback, and notification workflows into repositories and services.
2. Keep scheduled jobs thin: load active query, execute search, process domain events, update run timestamps.
3. Move route-heavy query create/edit logic into `app/searches/` services next.
4. Expand relevance around explicit interactions: relevant, not relevant, clicked, dismissed, notified, ignored, purchased.
5. Replace the current heuristic relevance scorer with a trained classifier behind the same service boundary when enough feedback exists.

## Additive schema direction

The compatibility model remains `UserQuery` for the current route, scheduler, and repository code. The next schema increment adds history and event tables around it instead of destructively splitting it:

- `SearchRun` records each scheduled, preview, manual, or recent/full execution attempt.
- `ItemObservation` records the item/query/search-run snapshot after hard filters and before relevance decisions.
- `ItemFeatureSnapshot` stores versioned feature dictionaries and relevance decisions for a query/item pair.
- `UserItemInteraction` stores explicit and implicit labels such as clicked, dismissed, relevant, not relevant, notified, ignored, or purchased.
- `DomainEvent` provides a durable handoff from search/relevance decisions to downstream processors.
- `NotificationRecord` audits attempted and completed notification deliveries.

Legacy `required_keywords` and `excluded_keywords` stay on `UserQuery` as hard filters. `ItemRelevanceFeedback`, `Feedback`, `UserQueryItems`, `Keyword`, and `Item` remain available while services move toward learned preference and relevance.

## Deferred saved search split

Do not split `UserQuery` in the current additive pass. Once repositories and route code depend on domain interfaces instead of the legacy model, introduce compatible tables with a backfill migration:

- `saved_searches`: stable search identity, owner, marketplace, active flag, and keyword reference.
- `search_info`: user-editable filters and display metadata, including hard keyword filters.
- `search_status`: schedule and execution state such as first run, last full/recent run, and next full run.

The target application contract should continue to expose `SavedSearch`, `SearchFilters`, and `SearchSchedule`, with `saved_search_from_model(user_query)` and `to_ebay_search_params(saved_search)` preserving existing behavior during the transition.

## Configuration

Committed eBay credentials were removed. Configure eBay access with either:

- `EBAY_CREDENTIALS_JSON`, a JSON array of `{ "client_id": "...", "client_secret": "..." }` objects.
- `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` for a single credential pair.
