"""Credential loading and normalization for eBay API clients."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from ebay_client.auth.datetime_utils import parse_datetime

Credential = dict[str, Any]
Environment = Mapping[str, str]


def load_ebay_credentials(environ: Environment | None = None) -> list[Credential]:
    """Load eBay credentials from JSON or single credential environment variables."""
    env = os.environ if environ is None else environ
    json_value = _read_non_empty(env, "EBAY_CREDENTIALS_JSON")

    if json_value:
        return _load_json_credentials(json_value)

    return _load_single_env_credential(env)


def normalize_credential(raw_credential: Mapping[str, Any]) -> Credential:
    """Normalize one credential to the dict shape used by token providers."""
    client_id = _first_non_empty(
        raw_credential, "client_id", "clientId", "EBAY_CLIENT_ID"
    )
    client_secret = _first_non_empty(
        raw_credential,
        "client_secret",
        "clientSecret",
        "EBAY_CLIENT_SECRET",
    )

    if not client_id or not client_secret:
        raise ValueError("Each eBay credential requires client_id and client_secret")

    normalized = {
        "client_id": str(client_id),
        "client_secret": str(client_secret),
        "token": raw_credential.get("token"),
        "token_expiry": parse_datetime(raw_credential.get("token_expiry")),
    }

    if isinstance(raw_credential, dict):
        raw_credential.update(normalized)
        return raw_credential

    return normalized


def normalize_credentials(raw_credentials: object) -> list[Credential]:
    """Normalize a JSON credential payload into a list of credential dicts."""
    if isinstance(raw_credentials, Mapping):
        return [normalize_credential(raw_credentials)]

    if not isinstance(raw_credentials, list):
        raise ValueError("EBAY_CREDENTIALS_JSON must be a credential object or list")

    return [_normalize_list_item(credential) for credential in raw_credentials]


def _load_json_credentials(json_value: str) -> list[Credential]:
    try:
        parsed = json.loads(json_value)
    except json.JSONDecodeError as exc:
        raise ValueError("EBAY_CREDENTIALS_JSON contains invalid JSON") from exc

    return normalize_credentials(parsed)


def _normalize_list_item(raw_credential: object) -> Credential:
    if not isinstance(raw_credential, Mapping):
        raise ValueError("Each EBAY_CREDENTIALS_JSON item must be an object")
    return normalize_credential(raw_credential)


def _load_single_env_credential(env: Environment) -> list[Credential]:
    client_id = _read_non_empty(env, "EBAY_CLIENT_ID")
    client_secret = _read_non_empty(env, "EBAY_CLIENT_SECRET")

    if not client_id and not client_secret:
        return []

    if not client_id or not client_secret:
        raise ValueError("Both EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required")

    return [
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "token": None,
            "token_expiry": None,
        }
    ]


def _read_non_empty(env: Environment, key: str) -> str | None:
    value = env.get(key)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _first_non_empty(raw_credential: Mapping[str, Any], *keys: str) -> Any | None:
    for key in keys:
        value = raw_credential.get(key)
        if value is not None and str(value).strip():
            return value
    return None
