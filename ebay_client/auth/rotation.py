import logging

from .credentials import EbayCredential


logger = logging.getLogger(__name__)


class RotatedCredential:
    def __init__(self, raw):
        self.raw = raw
        self.credential = EbayCredential.from_mapping(raw)

    def __getattr__(self, name):
        return getattr(self.credential, name)

    @property
    def token(self):
        return self.credential.token

    @token.setter
    def token(self, value):
        self.credential.token = value
        self.raw["token"] = value

    @property
    def token_expiry(self):
        return self.credential.token_expiry

    @token_expiry.setter
    def token_expiry(self, value):
        self.credential.token_expiry = value
        self.raw["token_expiry"] = value


class CredentialRotator:
    def __init__(self, credentials, current_index=0):
        self.credentials = credentials or []
        self.current_index = current_index

    def next_credential(self):
        if not self.credentials:
            raise RuntimeError(
                "No eBay credentials configured. Set EBAY_CREDENTIALS_JSON or "
                "EBAY_CLIENT_ID/EBAY_CLIENT_SECRET."
            )

        credential = self.credentials[self.current_index]
        logger.debug("Using eBay credential index %s", self.current_index)
        self.current_index = (self.current_index + 1) % len(self.credentials)
        return RotatedCredential(credential)
