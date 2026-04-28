import json
from datetime import datetime, timedelta, timezone
from typing import Any

from ebay_client.auth import (
    CredentialRotator,
    EbayTokenProvider,
    InMemoryTokenStore,
    JsonTokenStore,
)
from ebay_client.auth.credentials import EbayCredential
from ebay_client.config.credentials import load_ebay_credentials

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"


class FakeOAuthClient:
    """Offline OAuth client test double for token provider tests."""

    def __init__(
        self,
        token: str = "fresh-token",
        ttl: timedelta = timedelta(hours=2),
    ) -> None:
        self.token = token
        self.ttl = ttl
        self.calls: list[str] = []

    def fetch_client_credentials_token(self, credential: Any) -> tuple[str, timedelta]:
        self.calls.append(credential.client_id)
        return self.token, self.ttl


def test_load_ebay_credentials_from_json_env() -> None:
    payload = json.dumps(
        [
            {
                "clientId": "json-client",
                "clientSecret": "json-secret",
                "token": "cached-token",
                "token_expiry": "2026-01-01T00:00:00+00:00",
            }
        ]
    )

    credentials = load_ebay_credentials({"EBAY_CREDENTIALS_JSON": payload})

    assert credentials == [
        {
            "client_id": "json-client",
            "client_secret": "json-secret",
            "token": "cached-token",
            "token_expiry": "2026-01-01T00:00:00+00:00",
        }
    ]


def test_load_ebay_credentials_from_single_env_fallback() -> None:
    credentials = load_ebay_credentials(
        {
            "EBAY_CLIENT_ID": "single-client",
            "EBAY_CLIENT_SECRET": "single-secret",
            "EBAY_ACCESS_TOKEN": "single-token",
        }
    )

    assert credentials == [
        {
            "client_id": "single-client",
            "client_secret": "single-secret",
            "token": "single-token",
            "token_expiry": None,
        }
    ]


def test_load_ebay_credentials_from_empty_env() -> None:
    assert load_ebay_credentials({}) == []


def test_get_token_refreshes_expired_credential() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ttl = timedelta(minutes=30)
    credentials = [
        {
            "client_id": "refresh-client",
            "client_secret": "refresh-secret",
            "token": None,
            "token_expiry": None,
        }
    ]
    oauth_client = FakeOAuthClient(ttl=ttl)
    provider = EbayTokenProvider(
        credentials=credentials,
        token_url=TOKEN_URL,
        oauth_client=oauth_client,
        token_store=InMemoryTokenStore(),
        clock=lambda: now,
    )

    token = provider.get_token()

    assert token == "fresh-token"
    assert oauth_client.calls == ["refresh-client"]
    assert credentials[0]["token"] == "fresh-token"
    assert credentials[0]["token_expiry"] == now + ttl


def test_get_token_uses_cached_token() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    credentials = [
        {
            "client_id": "cached-client",
            "client_secret": "cached-secret",
            "token": "cached-token",
            "token_expiry": now + timedelta(hours=1),
        }
    ]
    oauth_client = FakeOAuthClient()
    provider = EbayTokenProvider(
        credentials=credentials,
        token_url=TOKEN_URL,
        oauth_client=oauth_client,
        token_store=InMemoryTokenStore(),
        clock=lambda: now,
    )

    token = provider.get_token()

    assert token == "cached-token"
    assert oauth_client.calls == []


def test_provider_synchronizes_rotator_index_before_and_after_rotation() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    credentials = [
        {
            "client_id": "first-client",
            "client_secret": "first-secret",
            "token": "first-token",
            "token_expiry": now + timedelta(hours=1),
        },
        {
            "client_id": "second-client",
            "client_secret": "second-secret",
            "token": "second-token",
            "token_expiry": now + timedelta(hours=1),
        },
    ]
    rotator = CredentialRotator([], current_index=0)
    provider = EbayTokenProvider(
        credentials=credentials,
        token_url=TOKEN_URL,
        rotator=rotator,
        oauth_client=FakeOAuthClient(),
        token_store=InMemoryTokenStore(),
        clock=lambda: now,
    )
    provider.current_cred_index = 1

    token = provider.get_token()

    assert token == "second-token"
    assert rotator.credentials == credentials
    assert provider.current_cred_index == 0


def test_json_token_store_saves_and_loads_token_data(tmp_path) -> None:
    token_expiry = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)
    token_store = JsonTokenStore(tmp_path / "tokens.json")
    credential = EbayCredential(
        client_id="stored-client",
        client_secret="stored-secret",
        token="stored-token",
        token_expiry=token_expiry,
    )

    token_store.save(credential)
    loaded = token_store.load(
        {
            "client_id": "stored-client",
            "client_secret": "stored-secret",
        }
    )

    assert loaded.token == "stored-token"
    assert loaded.token_expiry == token_expiry


def test_json_token_store_parses_datetime_values(tmp_path) -> None:
    token_file = tmp_path / "tokens.json"
    token_file.write_text(
        json.dumps(
            {
                "datetime-client": {
                    "token": "datetime-token",
                    "token_expiry": "2026-01-01T12:30:00Z",
                }
            }
        ),
        encoding="utf-8",
    )

    loaded = JsonTokenStore(token_file).load(
        {
            "client_id": "datetime-client",
            "client_secret": "datetime-secret",
        }
    )

    assert loaded.token == "datetime-token"
    assert loaded.token_expiry == datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)
