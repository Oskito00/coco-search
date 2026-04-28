from datetime import datetime, timezone
import os
from pathlib import Path

from .expiry import TokenExpiryPolicy
from .oauth import EbayOAuthClient
from .rotation import CredentialRotator
from .token_store import JsonTokenStore


class EbayTokenProvider:
    """Provides valid eBay OAuth bearer tokens using rotating credentials."""

    def __init__(
        self,
        credentials,
        token_url,
        session=None,
        rotator=None,
        oauth_client=None,
        token_store=None,
        expiry_policy=None,
        clock=None,
    ):
        self.credentials = credentials or []
        self.current_cred_index = 0
        self.token_url = token_url
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.token_store = token_store or JsonTokenStore(_default_token_store_path())
        self.expiry_policy = expiry_policy or TokenExpiryPolicy(clock=self.clock)
        self.oauth_client = oauth_client or EbayOAuthClient(token_url, session=session)
        self.rotator = rotator or CredentialRotator(self.credentials)

    def _sync_rotator(self):
        self.rotator.credentials = self.credentials
        self.rotator.current_index = self.current_cred_index

    def _sync_index(self):
        self.current_cred_index = self.rotator.current_index

    def _get_current_credential(self):
        self._sync_rotator()
        credential = self.token_store.load(self.rotator.next_credential())
        self._sync_index()
        return credential.raw

    def _token_needs_refresh(self, cred):
        credential = self.token_store.load(cred)
        return self.expiry_policy.needs_refresh(credential)

    def get_token(self):
        self._sync_rotator()
        credential = self.token_store.load(self.rotator.next_credential())
        self._sync_index()

        if self.expiry_policy.needs_refresh(credential):
            token, ttl = self.oauth_client.fetch_client_credentials_token(credential)
            credential.token = token
            credential.token_expiry = self.clock() + ttl
            self.token_store.save(credential)

        return credential.token


def _default_token_store_path():
    return Path(os.getenv("EBAY_TOKEN_STORE_PATH", ".local/ebay_tokens.json"))
