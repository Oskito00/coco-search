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

## Configuration

Committed eBay credentials were removed. Configure eBay access with either:

- `EBAY_CREDENTIALS_JSON`, a JSON array of `{ "client_id": "...", "client_secret": "..." }` objects.
- `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` for a single credential pair.
