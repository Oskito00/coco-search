from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from ebay_client.auth.datetime_utils import parse_datetime
from ebay_client.auth.provider import EbayTokenProvider
from ebay_client.auth.token_store import EbayTokenStore, load_tokens, save_tokens
from ebay_client.config.credentials import load_ebay_credentials


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def json(self) -> dict[str, Any]:
        return self.payload

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def post(self, *args: Any, **kwargs: Any) -> FakeResponse:
        self.calls.append({"args": args, "kwargs": kwargs})
        return FakeResponse(self.payload)


def test_load_ebay_credentials_from_json_env() -> None:
    expires_at = "2026-04-28T12:00:00Z"
    environ = {
        "EBAY_CREDENTIALS_JSON": json.dumps(
            [
                {
                    "client_id": "client-json",
                    "client_secret": "secret-json",
                    "token": "cached",
                    "token_expiry": expires_at,
                }
            ]
        )
    }

    credentials = load_ebay_credentials(environ)

    assert credentials == [
        {
            "client_id": "client-json",
            "client_secret": "secret-json",
            "token": "cached",
            "token_expiry": datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
        }
    ]


def test_load_ebay_credentials_from_single_env_fallback() -> None:
    credentials = load_ebay_credentials(
        {
            "EBAY_CLIENT_ID": "client-env",
            "EBAY_CLIENT_SECRET": "secret-env",
        }
    )

    assert credentials == [
        {
            "client_id": "client-env",
            "client_secret": "secret-env",
            "token": None,
            "token_expiry": None,
        }
    ]


def test_load_ebay_credentials_empty_env_returns_empty_list() -> None:
    assert load_ebay_credentials({}) == []


def test_get_token_refreshes_expired_credential_and_syncs_index() -> None:
    session = FakeSession({"access_token": "fresh-token", "expires_in": 3600})
    credentials = [
        {
            "client_id": "client-refresh",
            "client_secret": "secret-refresh",
            "token": None,
            "token_expiry": None,
        }
    ]
    provider = EbayTokenProvider(credentials=credentials, session=session)

    token = provider.get_token()

    assert token == "fresh-token"
    assert provider.current_cred_index == 0
    assert provider.credentials[0]["token"] == "fresh-token"
    assert credentials[0]["token"] == "fresh-token"
    assert provider.credentials[0]["token_expiry"] > datetime.now(timezone.utc)
    assert session.calls[0]["kwargs"]["auth"] == ("client-refresh", "secret-refresh")
    assert session.calls[0]["kwargs"]["data"] == {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }


def test_get_token_returns_cached_token_without_refresh() -> None:
    session = FakeSession({"access_token": "unused-token", "expires_in": 3600})
    provider = EbayTokenProvider(
        credentials=[
            {
                "client_id": "client-cached",
                "client_secret": "secret-cached",
                "token": "cached-token",
                "token_expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            }
        ],
        session=session,
    )

    assert provider.get_token() == "cached-token"
    assert session.calls == []


def test_token_store_save_and_load_round_trip(tmp_path: Any) -> None:
    path = tmp_path / "tokens.json"
    expiry = datetime(2026, 4, 28, 13, 30, tzinfo=timezone.utc)

    save_tokens(
        path,
        {
            "client-store": {
                "token": "stored-token",
                "token_expiry": expiry,
            }
        },
    )

    assert load_tokens(path) == {
        "client-store": {
            "token": "stored-token",
            "token_expiry": expiry,
        }
    }


def test_provider_loads_and_saves_through_token_store(tmp_path: Any) -> None:
    path = tmp_path / "tokens.json"
    store = EbayTokenStore(path)
    store.save(
        {
            "client-store": {
                "token": "stored-token",
                "token_expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            }
        }
    )
    provider = EbayTokenProvider(
        credentials=[
            {
                "client_id": "client-store",
                "client_secret": "secret-store",
                "token": None,
                "token_expiry": None,
            }
        ],
        token_store=store,
    )

    assert provider.get_token() == "stored-token"


def test_parse_datetime_accepts_z_suffix_and_naive_values() -> None:
    assert parse_datetime("2026-04-28T12:00:00Z") == datetime(
        2026,
        4,
        28,
        12,
        0,
        tzinfo=timezone.utc,
    )
    assert parse_datetime("2026-04-28T12:00:00") == datetime(
        2026,
        4,
        28,
        12,
        0,
        tzinfo=timezone.utc,
    )
