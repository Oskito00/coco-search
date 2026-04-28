import json
import os


def load_ebay_credentials(environ=None):
    """Load eBay credential rotation config from environment variables."""
    environ = environ or os.environ
    credentials_json = environ.get("EBAY_CREDENTIALS_JSON")

    if credentials_json:
        credentials = json.loads(credentials_json)
        return [_normalise_credential(credential) for credential in credentials]

    client_id = environ.get("EBAY_CLIENT_ID")
    client_secret = environ.get("EBAY_CLIENT_SECRET")
    if client_id and client_secret:
        return [
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "token": environ.get("EBAY_ACCESS_TOKEN"),
                "token_expiry": None,
            }
        ]

    return []


def _normalise_credential(credential):
    return {
        "client_id": credential.get("client_id") or credential.get("clientId"),
        "client_secret": credential.get("client_secret") or credential.get("clientSecret"),
        "token": credential.get("token"),
        "token_expiry": credential.get("token_expiry"),
    }
