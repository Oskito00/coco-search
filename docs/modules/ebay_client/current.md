# eBay Client Module - Current State

## Auth package

Authentication now lives under `ebay_client/auth/` instead of a single `auth.py` file.

Current files:

- `auth/__init__.py` exports the public auth API.
- `auth/credentials.py` defines `EbayCredential`.
- `auth/rotation.py` defines `CredentialRotator` and handles round-robin credential selection.
- `auth/expiry.py` defines `TokenExpiryPolicy` and handles token refresh timing.
- `auth/oauth.py` defines `EbayOAuthClient` and owns the eBay OAuth token HTTP request.
- `auth/token_store.py` defines `TokenStore`, `InMemoryTokenStore`, and `JsonTokenStore`.
- `auth/provider.py` defines `EbayTokenProvider`, the main public token provider.

## Token storage

The default token store is now JSON-backed.

Default path:

```text
.local/ebay_tokens.json
```

Override path:

```bash
EBAY_TOKEN_STORE_PATH=/path/to/ebay_tokens.json
```

The real local token store is ignored by git via `.local/`.

Tracked example skeleton:

```text
docs/modules/ebay_client/token_store.example.json
```

## Package name

The eBay client package is now named `ebay_client`, which is a valid Python package name.

Imports in the current app code have been updated from `app.ebay.*` to `ebay_client.*`.

## SDK entry point

`ebay_client.EbayClient` is the public SDK object. It composes auth and endpoint clients, and exposes methods for the eBay endpoints currently supported by the app.

Current endpoint methods:

- `search_item_summaries(...)` for `GET /buy/browse/v1/item_summary/search`.
- `search_items(...)` for paginated search plus SDK response parsing.
- `get_rate_limits()` for `GET /developer/analytics/v1_beta/rate_limit`.
- `get_browse_limits(...)` and `get_search_limits(...)` for rate-limit extraction helpers.

The SDK no longer imports Flask, SQLAlchemy, app utilities, Stripe/billing code, or Coco search filtering.

## Current package layout

```text
ebay_client/
  __init__.py
  api.py
  analytics/
    client.py
    rate_limits.py
  auth/
    credentials.py
    expiry.py
    oauth.py
    provider.py
    rotation.py
    token_store.py
  browse/
    client.py
    dto.py
    filters.py
    parsers.py
    responses.py
  config/
    credentials.py
    env.py
  conditions.py
  marketplaces.py
  time.py
```
