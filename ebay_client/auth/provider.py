"""OAuth token provider for eBay client-credentials auth."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol, cast

import requests  # type: ignore[import-untyped]

from ebay_client.auth.rotation import CredentialRotator
from ebay_client.auth.token_store import EbayTokenStore
from ebay_client.config.credentials import load_ebay_credentials, normalize_credentials

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
DEFAULT_SCOPE = "https://api.ebay.com/oauth/api_scope"
FORM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}

Credential = dict[str, Any]


class TokenStore(Protocol):
    """Protocol for token stores used by the provider."""

    def apply_to_credentials(self, credentials: list[Credential]) -> None:
        """Apply persisted token fields to credentials."""

    def update_credential(self, credential: Credential) -> None:
        """Persist token fields from a credential."""


class EbayTokenProvider:
    """Provide cached or freshly refreshed eBay OAuth access tokens."""

    def __init__(
        self,
        credentials: Iterable[Mapping[str, Any]] | Mapping[str, Any] | None = None,
        token_store: TokenStore | str | Path | None = None,
        session: requests.Session | None = None,
        token_url: str = TOKEN_URL,
        scope: str | Iterable[str] = DEFAULT_SCOPE,
        refresh_margin: timedelta = timedelta(seconds=60),
        environ: Mapping[str, str] | None = None,
        request_timeout: float = 30.0,
        start_index: int = 0,
    ) -> None:
        """Create a token provider while preserving constructor flexibility."""
        raw_credentials = (
            credentials if credentials is not None else load_ebay_credentials(environ)
        )
        self.credentials = normalize_credentials(raw_credentials)
        self.token_store = _build_token_store(token_store)
        self.session = session or requests.Session()
        self.token_url = token_url
        self.scope = _normalize_scope(scope)
        self.refresh_margin = refresh_margin
        self.request_timeout = request_timeout
        self._rotator = CredentialRotator(self.credentials, start_index)
        self._load_stored_tokens()

    @property
    def current_cred_index(self) -> int:
        """Return the index that will be used for the next credential."""
        return self._rotator.index

    @current_cred_index.setter
    def current_cred_index(self, value: int) -> None:
        self._rotator.index = value

    def get_token(self) -> str:
        """Return an access token, refreshing the selected credential if needed."""
        credential = self._get_current_credential()
        if self._token_needs_refresh(credential):
            self._refresh_credential(credential)
        return str(credential["token"])

    def _get_token(self) -> str:
        """Backward-compatible alias for older internal callers."""
        return self.get_token()

    def _get_current_credential(self) -> Credential:
        """Return the next round-robin credential."""
        return self._rotator.next()

    def _token_needs_refresh(self, credential: Mapping[str, Any]) -> bool:
        """Return whether the credential lacks a reusable access token."""
        token = credential.get("token")
        token_expiry = credential.get("token_expiry")

        if not token or not token_expiry:
            return True

        return _utc_now() > token_expiry - self.refresh_margin

    def _refresh_credential(self, credential: Credential) -> None:
        """Refresh one credential and persist its token fields."""
        token_data = self._request_token(credential)
        credential["token"] = token_data["access_token"]
        credential["token_expiry"] = _utc_now() + timedelta(
            seconds=int(token_data["expires_in"])
        )
        self._save_credential(credential)

    def _request_token(self, credential: Mapping[str, Any]) -> Mapping[str, Any]:
        """Request a fresh OAuth token for one eBay credential."""
        response = self.session.post(
            self.token_url,
            auth=(credential["client_id"], credential["client_secret"]),
            headers=FORM_HEADERS,
            data={
                "grant_type": "client_credentials",
                "scope": self.scope,
            },
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        token_data = response.json()
        _validate_token_response(token_data)
        return token_data

    def _load_stored_tokens(self) -> None:
        if self.token_store is not None:
            self.token_store.apply_to_credentials(self.credentials)

    def _save_credential(self, credential: Credential) -> None:
        if self.token_store is not None:
            self.token_store.update_credential(credential)


def _build_token_store(
    token_store: TokenStore | str | Path | None,
) -> TokenStore | None:
    if token_store is None:
        return None
    if _has_token_store_methods(token_store):
        return cast(TokenStore, token_store)
    return EbayTokenStore(cast(str | Path, token_store))


def _has_token_store_methods(candidate: object) -> bool:
    return hasattr(candidate, "apply_to_credentials") and hasattr(
        candidate, "update_credential"
    )


def _normalize_scope(scope: str | Iterable[str]) -> str:
    if isinstance(scope, str):
        return scope
    return " ".join(scope)


def _validate_token_response(token_data: Mapping[str, Any]) -> None:
    if "access_token" not in token_data or "expires_in" not in token_data:
        raise ValueError("eBay token response missing access_token or expires_in")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
