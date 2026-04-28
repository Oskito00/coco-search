import json
from datetime import datetime
from pathlib import Path

from .credentials import EbayCredential


class TokenStore:
    def load(self, credential):
        raise NotImplementedError

    def save(self, credential):
        raise NotImplementedError


class InMemoryTokenStore(TokenStore):
    def load(self, credential):
        if hasattr(credential, "raw"):
            return credential
        if isinstance(credential, EbayCredential):
            return credential
        return EbayCredential.from_mapping(credential)

    def save(self, credential):
        if hasattr(credential, "raw"):
            credential.raw.update(
                {
                    "token": credential.token,
                    "token_expiry": credential.token_expiry,
                }
            )
        return credential


class JsonTokenStore(TokenStore):
    def __init__(self, path):
        self.path = Path(path)

    def load(self, credential):
        loaded = InMemoryTokenStore().load(credential)
        tokens = self._read_tokens()
        token_data = tokens.get(loaded.client_id)
        if token_data:
            loaded.token = token_data.get("token")
            loaded.token_expiry = _parse_datetime(token_data.get("token_expiry"))
        return loaded

    def save(self, credential):
        tokens = self._read_tokens()
        tokens[credential.client_id] = {
            "token": credential.token,
            "token_expiry": (
                credential.token_expiry.isoformat()
                if credential.token_expiry is not None
                else None
            ),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        tmp_path.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)
        InMemoryTokenStore().save(credential)
        return credential

    def _read_tokens(self):
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))


def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
