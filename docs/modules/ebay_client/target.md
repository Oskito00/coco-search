# eBay Client Module - Target State

## Package shape

The eBay client should become a clean, packageable module with no Flask dependency in the core client/auth code.

Recommended final package name:

```text
ebay_client/
```

Target structure:

```text
ebay_client/
  __init__.py
  api.py
  analytics/
    client.py
    dto.py
    rate_limits.py
  auth/
    __init__.py
    credentials.py
    rotation.py
    expiry.py
    oauth.py
    token_store.py
    provider.py
  browse/
    client.py
    dto.py
    filters.py
    pagination.py
    parsers.py
    responses.py
  config/
    credentials.py
    env.py
  conditions.py
  marketplaces.py
  time.py
```

## Auth target

Auth should stay split by responsibility:

- `EbayCredential`: typed credential object.
- `CredentialRotator`: selects credentials in round-robin order.
- `TokenExpiryPolicy`: decides whether a token needs refresh.
- `EbayOAuthClient`: talks to eBay OAuth.
- `TokenStore`: persistence interface.
- `JsonTokenStore`: local JSON token persistence.
- `EbayTokenProvider`: public facade that returns valid bearer tokens.

## Token storage target

JSON token storage is acceptable for the current local/refactor stage.

Longer term, production SaaS deployment should probably move token persistence to Postgres or another shared store, because JSON files are fragile with multiple workers, containers, and ephemeral filesystems.

## Dependency target

The reusable eBay client should not depend on:

- Flask or `current_app`
- SQLAlchemy models
- Coco search/relevance rules
- Notification code
- Stripe/billing constants

The app layer can still adapt Flask config into the eBay client at the boundary.
