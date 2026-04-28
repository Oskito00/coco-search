"""API token issuance, verification, and revocation."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from app.extensions import db
from app.models import ApiToken, User

TOKEN_PREFIX = "cs"
TOKEN_BYTES = 32  # → 43-char urlsafe string


@dataclass(frozen=True)
class IssuedToken:
    """Returned once at creation time. The raw token is never persisted."""

    raw: str
    record: ApiToken


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _generate_raw_token() -> str:
    return f"{TOKEN_PREFIX}_{secrets.token_urlsafe(TOKEN_BYTES)}"


def issue_token(
    user: User,
    name: str,
    scopes: Iterable[str],
    expires_at: datetime | None = None,
) -> IssuedToken:
    raw = _generate_raw_token()
    record = ApiToken(
        user_id=user.id,
        name=name,
        token_prefix=raw[: len(TOKEN_PREFIX) + 1 + 8],
        token_hash=hash_token(raw),
        scopes=list(scopes),
        expires_at=expires_at,
    )
    db.session.add(record)
    db.session.flush()
    return IssuedToken(raw=raw, record=record)


def verify_token(raw: str) -> ApiToken | None:
    """Look up a token by hash. Returns the active record or None."""
    if not raw:
        return None
    record = ApiToken.query.filter_by(token_hash=hash_token(raw)).first()
    if record is None or not _is_active(record):
        return None
    return record


def revoke_token(record: ApiToken) -> None:
    record.revoked_at = datetime.utcnow()
    db.session.flush()


def _is_active(record: ApiToken) -> bool:
    if record.revoked_at is not None:
        return False
    if record.expires_at is not None and record.expires_at <= datetime.utcnow():
        return False
    return True
