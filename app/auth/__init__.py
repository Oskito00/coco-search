"""Authentication primitives: scopes, API tokens, email tokens."""

from app.auth.scopes import (
    SCOPE_ADMIN,
    SCOPE_NOTIFICATIONS_READ,
    SCOPE_NOTIFICATIONS_WRITE,
    SCOPE_SEARCHES_READ,
    SCOPE_SEARCHES_WRITE,
    SCOPE_SUBSCRIPTION_WRITE,
    SCOPE_USER_READ,
    SCOPE_USER_WRITE,
    DEFAULT_SCOPES,
    ALL_SCOPES,
)
from app.auth.tokens import (
    issue_token,
    verify_token,
    revoke_token,
    hash_token,
)
from app.auth.email_tokens import (
    generate_email_token,
    confirm_email_token,
)

__all__ = [
    "SCOPE_ADMIN",
    "SCOPE_NOTIFICATIONS_READ",
    "SCOPE_NOTIFICATIONS_WRITE",
    "SCOPE_SEARCHES_READ",
    "SCOPE_SEARCHES_WRITE",
    "SCOPE_SUBSCRIPTION_WRITE",
    "SCOPE_USER_READ",
    "SCOPE_USER_WRITE",
    "DEFAULT_SCOPES",
    "ALL_SCOPES",
    "issue_token",
    "verify_token",
    "revoke_token",
    "hash_token",
    "generate_email_token",
    "confirm_email_token",
]
