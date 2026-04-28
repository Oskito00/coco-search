# eBay Client Module - Tasks

## Done

- [x] Split single `auth.py` into `ebay_client/auth/`.
- [x] Added `EbayCredential` in `auth/credentials.py`.
- [x] Added `CredentialRotator` in `auth/rotation.py`.
- [x] Added `TokenExpiryPolicy` in `auth/expiry.py`.
- [x] Added `EbayOAuthClient` in `auth/oauth.py`.
- [x] Added `TokenStore`, `InMemoryTokenStore`, and `JsonTokenStore` in `auth/token_store.py`.
- [x] Added `EbayTokenProvider` in `auth/provider.py`.
- [x] Made JSON token storage the default.
- [x] Added `EBAY_TOKEN_STORE_PATH` override support.
- [x] Added `.local/` to `.gitignore`.
- [x] Created local ignored token store skeleton at `.local/ebay_tokens.json`.
- [x] Added tracked example skeleton at `docs/modules/ebay_client/token_store.example.json`.
- [x] Verified auth package compilation.
- [x] Verified JSON token write/read behavior with a temporary token file.
- [x] Rename `app/ebay-client` to `ebay_client`.
- [x] Update imports from `app.ebay.*` to `ebay_client.*`.
- [x] Replace legacy `EbayAPI` facade with `EbayClient` SDK entry point.
- [x] Remove Flask/current_app dependency from `ebay_client`.
- [x] Move Coco keyword filtering out of `ebay_client` and into `app/searches`.
- [x] Remove legacy `RotatingOAuthTokenProvider` alias from SDK exports.
- [x] Move `ebay_client` to a top-level package so importing the SDK does not execute `app/__init__.py`.
- [x] Move Stripe tier constants out of `ebay_client.constants` and into `app/billing/constants.py`.
- [x] Remove `tenacity` dependency from the SDK client.
- [x] Verify top-level `ebay_client` import and core behavior with a mocked session.
- [x] Split marketplace and condition constants into `marketplaces.py` and `conditions.py`.
- [x] Move Browse DTOs into `browse/dto.py`.
- [x] Move Browse filter building into `browse/filters.py`.
- [x] Move Browse response parsing into `browse/parsers.py`.
- [x] Move eBay datetime parsing into `time.py`.
- [x] Move dedupe helper into `browse/responses.py`.
- [x] Move analytics rate-limit endpoint code into `analytics/client.py`.
- [x] Move rate-limit extraction into `analytics/rate_limits.py`.
- [x] Convert `config.py` into a `config/` package with credential/env modules.

## Next

- [ ] Add unit tests for `CredentialRotator`.
- [ ] Add unit tests for `TokenExpiryPolicy`.
- [ ] Add unit tests for `JsonTokenStore`.
- [ ] Add unit tests for `EbayTokenProvider`.
- [ ] Decide whether real production token storage stays JSON or moves to Postgres.
- [ ] Add a small README/example for standalone SDK usage.
- [ ] Add `analytics/dto.py` if rate-limit responses need typed objects.
- [ ] Add `browse/pagination.py` if pagination grows beyond the current loop.
