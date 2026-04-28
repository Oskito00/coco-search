import json
import os
from typing import Any, Mapping, Optional


def load_ebay_credentials(
    environ: Optional[Mapping[str, str]] = None,
) -> list[dict[str, Any]]:
    """Load eBay credential rotation config from environment variables."""
    env = _environment(environ)
    credentials_json = _credentials_json(env)

    if credentials_json:
        return _credentials_from_json(credentials_json)

    credential = _credential_from_single_env(env)
    if credential:
        return [credential]
    return []


def _environment(environ: Optional[Mapping[str, str]]) -> Mapping[str, str]:
    """Return the supplied environment mapping or process environment."""
    return os.environ if environ is None else environ


def _credentials_json(environ: Mapping[str, str]) -> Optional[str]:
    """Return the JSON credential payload from the environment."""
    return environ.get("EBAY_CREDENTIALS_JSON")


def _credentials_from_json(credentials_json: str) -> list[dict[str, Any]]:
    """Parse and normalize JSON credential rotation data."""
    credentials = json.loads(credentials_json)
    return [_normalise_credential(credential) for credential in credentials]


def _credential_from_single_env(
    environ: Mapping[str, str],
) -> Optional[dict[str, Any]]:
    """Build a single credential from legacy client ID/secret variables."""
    client_id = environ.get("EBAY_CLIENT_ID")
    client_secret = environ.get("EBAY_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "token": environ.get("EBAY_ACCESS_TOKEN"),
        "token_expiry": None,
    }


def _normalise_credential(credential: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize supported credential key spellings to snake case."""
    return {
        "client_id": credential.get("client_id") or credential.get("clientId"),
        "client_secret": credential.get("client_secret")
        or credential.get("clientSecret"),
        "token": credential.get("token"),
        "token_expiry": credential.get("token_expiry"),
    }
