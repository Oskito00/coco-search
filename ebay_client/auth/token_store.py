import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

from .credentials import EbayCredential


class TokenStore:
    def load(self, credential: Any) -> Any:
        """Return a credential object with any persisted token data applied."""
        raise NotImplementedError

    def save(self, credential: Any) -> Any:
        """Persist token data for a credential."""
        raise NotImplementedError


class InMemoryTokenStore(TokenStore):
    def load(self, credential: Any) -> Any:
        """Coerce mapping credentials while preserving rotator wrappers."""
        return _coerce_credential(credential)

    def save(self, credential: Any) -> Any:
        """Persist token data back to a wrapped raw mapping when present."""
        if hasattr(credential, "raw"):
            _update_raw_credential(credential)
        return credential


class JsonTokenStore(TokenStore):
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)

    def load(self, credential: Any) -> Any:
        """Load persisted token data for the supplied credential."""
        loaded = _coerce_credential(credential)
        tokens = self._read_tokens()
        token_data = tokens.get(loaded.client_id)
        if token_data:
            _apply_token_data(loaded, token_data)
        return loaded

    def save(self, credential: Any) -> Any:
        """Persist a credential token cache to disk atomically."""
        tokens = self._read_tokens()
        tokens[credential.client_id] = _serialize_token_data(credential)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write_tokens(tokens)
        InMemoryTokenStore().save(credential)
        return credential

    def _read_tokens(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        with self.path.open(encoding="utf-8") as token_file:
            return json.load(token_file)

    def _write_tokens(self, tokens: dict[str, dict[str, Any]]) -> None:
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        with tmp_path.open("w", encoding="utf-8") as token_file:
            json.dump(tokens, token_file, indent=2)
        tmp_path.replace(self.path)


def _coerce_credential(credential: Any) -> Any:
    """Return a credential object while preserving rotator wrappers."""
    if hasattr(credential, "raw"):
        return credential
    if isinstance(credential, EbayCredential):
        return credential
    return EbayCredential.from_mapping(credential)


def _update_raw_credential(credential: Any) -> None:
    """Write token fields back to a rotator wrapper's raw mapping."""
    credential.raw.update(
        {
            "token": credential.token,
            "token_expiry": credential.token_expiry,
        }
    )


def _apply_token_data(credential: Any, token_data: dict[str, Any]) -> None:
    """Apply serialized token fields to a credential."""
    credential.token = token_data.get("token")
    credential.token_expiry = _parse_datetime(token_data.get("token_expiry"))


def _serialize_token_data(credential: Any) -> dict[str, Optional[str]]:
    """Convert credential token fields into JSON-safe values."""
    return {
        "token": credential.token,
        "token_expiry": _serialize_datetime(credential.token_expiry),
    }


def _serialize_datetime(value: Optional[datetime]) -> Optional[str]:
    """Serialize an optional datetime for token storage."""
    if value is None:
        return None
    return value.isoformat()


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse token expiry values loaded from JSON."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(_normalize_datetime_value(value))


def _normalize_datetime_value(value: str) -> str:
    """Normalize common UTC suffixes for datetime.fromisoformat."""
    if value.endswith("Z"):
        return f"{value[:-1]}+00:00"
    return value
