from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Callable, Optional

from .expiry import TokenExpiryPolicy
from .oauth import EbayOAuthClient
from .rotation import CredentialRotator
from .token_store import JsonTokenStore, TokenStore

Clock = Callable[[], datetime]


class EbayTokenProvider:
    """Provides valid eBay OAuth bearer tokens using rotating credentials."""

    def __init__(
        self,
        credentials: Any,
        token_url: str,
        session: Any = None,
        rotator: Optional[CredentialRotator] = None,
        oauth_client: Any = None,
        token_store: Optional[TokenStore] = None,
        expiry_policy: Optional[TokenExpiryPolicy] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self.credentials = credentials or []
        self.current_cred_index = 0
        self.token_url = token_url
        self.clock = _resolve_clock(clock)
        self.token_store = _resolve_token_store(token_store)
        self.expiry_policy = _resolve_expiry_policy(expiry_policy, self.clock)
        self.oauth_client = _resolve_oauth_client(oauth_client, token_url, session)
        self.rotator = _resolve_rotator(rotator, self.credentials)

    def _sync_rotator(self) -> None:
        """Copy provider rotation state into the configured rotator."""
        self.rotator.credentials = self.credentials
        self.rotator.current_index = self.current_cred_index

    def _sync_index(self) -> None:
        """Copy rotator position back to the public provider index."""
        self.current_cred_index = self.rotator.current_index

    def _get_current_credential(self) -> Any:
        credential = self._load_next_credential()
        return credential.raw

    def _token_needs_refresh(self, cred: Any) -> bool:
        credential = self._load_credential(cred)
        return self.expiry_policy.needs_refresh(credential)

    def get_token(self) -> Optional[str]:
        """Return a valid token, refreshing the current credential when needed."""
        credential = self._load_next_credential()

        if self.expiry_policy.needs_refresh(credential):
            self._refresh_token(credential)

        return credential.token

    def _load_next_credential(self) -> Any:
        """Rotate to the next credential and load its persisted token state."""
        self._sync_rotator()
        credential = self._load_credential(self.rotator.next_credential())
        self._sync_index()
        return credential

    def _load_credential(self, credential: Any) -> Any:
        """Load token state for a specific credential object or mapping."""
        return self.token_store.load(credential)

    def _refresh_token(self, credential: Any) -> None:
        """Fetch and persist a fresh OAuth token for a credential."""
        token, ttl = self.oauth_client.fetch_client_credentials_token(credential)
        credential.token = token
        credential.token_expiry = self.clock() + ttl
        self.token_store.save(credential)


def _resolve_clock(clock: Optional[Clock]) -> Clock:
    """Return the injected clock or the default UTC clock."""
    return clock or _default_clock


def _default_clock() -> datetime:
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


def _resolve_token_store(token_store: Optional[TokenStore]) -> TokenStore:
    """Return the injected token store or the default JSON store."""
    return token_store or JsonTokenStore(_default_token_store_path())


def _resolve_expiry_policy(
    expiry_policy: Optional[TokenExpiryPolicy],
    clock: Clock,
) -> TokenExpiryPolicy:
    """Return the injected expiry policy or one bound to the provider clock."""
    return expiry_policy or TokenExpiryPolicy(clock=clock)


def _resolve_oauth_client(
    oauth_client: Any,
    token_url: str,
    session: Any,
) -> Any:
    """Return the injected OAuth client or the default client."""
    return oauth_client or EbayOAuthClient(token_url, session=session)


def _resolve_rotator(
    rotator: Optional[CredentialRotator],
    credentials: Any,
) -> CredentialRotator:
    """Return the injected rotator or a rotator for provider credentials."""
    return rotator or CredentialRotator(credentials)


def _default_token_store_path() -> Path:
    """Return the configured token store path."""
    return Path(os.getenv("EBAY_TOKEN_STORE_PATH", ".local/ebay_tokens.json"))
