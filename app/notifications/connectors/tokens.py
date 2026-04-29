"""Time-bound, signed link tokens used by messaging connectors.

These tokens carry just enough information to identify which user clicked
through to a third-party messenger. They piggy-back on the same itsdangerous
serializer used for email confirmation, with a distinct salt per connector
kind so token reuse across surfaces is impossible.
"""

from __future__ import annotations

from typing import Optional

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

DEFAULT_LINK_TTL_SECONDS = 600  # 10 minutes
SALT_PREFIX = "messaging-link"


class LinkTokenService:
    """Mint and verify short-lived account-linking tokens."""

    def __init__(self, ttl_seconds: int = DEFAULT_LINK_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds

    def mint(self, user_id: int, kind: str) -> str:
        """Return a signed token binding a *user_id* to the given connector *kind*."""
        return self._serializer().dumps(int(user_id), salt=self._salt(kind))

    def verify(self, token: str, kind: str) -> Optional[int]:
        """Return the user id encoded in *token*, or None when invalid/expired."""
        try:
            user_id = self._serializer().loads(
                token, salt=self._salt(kind), max_age=self.ttl_seconds
            )
        except (BadSignature, SignatureExpired):
            return None
        return int(user_id)

    @staticmethod
    def _serializer() -> URLSafeTimedSerializer:
        return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

    @staticmethod
    def _salt(kind: str) -> str:
        return f"{SALT_PREFIX}:{kind}"
