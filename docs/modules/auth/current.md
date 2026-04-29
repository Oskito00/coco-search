# `app/auth/` — Current State

Token-based authentication for the JSON API. The original session/cookie
auth is gone; every protected route now requires a bearer token.

## Token lifecycle

`tokens.py` issues, hashes, and verifies API tokens.

- A token is `cs_<43 url-safe characters>` (prefix + 32 random bytes →
  `secrets.token_urlsafe`).
- The raw token is shown to the user **once** at creation time
  (`IssuedToken.raw`). Only `sha256(raw)` is stored in `api_tokens.token_hash`.
- Lookups use the 12-character `token_prefix` to narrow the index, then
  hash-compare to authenticate. Constant-time comparison via `hmac.compare_digest`.

## Scopes

`scopes.py` defines OAuth-style scope constants. Routes declare the scope
they need via `@require_auth(SCOPE_...)`:

```
SCOPE_USER_READ            user:read
SCOPE_USER_WRITE           user:write
SCOPE_SEARCHES_READ        searches:read
SCOPE_SEARCHES_WRITE       searches:write
SCOPE_NOTIFICATIONS_READ   notifications:read
SCOPE_NOTIFICATIONS_WRITE  notifications:write
SCOPE_SUBSCRIPTION_WRITE   subscription:write
SCOPE_ADMIN                admin
```

`DEFAULT_SCOPES` is what end-user tokens get; `ALL_SCOPES` adds admin.

## Email tokens

`email_tokens.py` mints / validates time-bound tokens for email
confirmation and password reset, signed with
`itsdangerous.URLSafeTimedSerializer` and the per-app `SECURITY_PASSWORD_SALT`.

The same itsdangerous primitive (with a different salt) is reused by
`app.notifications.connectors.tokens.LinkTokenService` for the Telegram
deep-link handshake.

## Current package layout

```text
app/auth/
  __init__.py             (exports SCOPE_* constants + token helpers)
  email_tokens.py         (email confirm / password reset tokens)
  scopes.py               (scope constants)
  tokens.py               (API token issue / verify / revoke + hashing)
```
