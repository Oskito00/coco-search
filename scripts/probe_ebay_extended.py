"""One-off probe: does fieldgroups=EXTENDED return shortDescription + aspects?

Reads ebay_credentials.json from the repo root, gets a token via the existing
SDK token provider, then hits the Browse search endpoint twice — once with the
default response, once with fieldgroups=EXTENDED — and prints the diff.

Run from repo root:
    python -m scripts.probe_ebay_extended "iphone 13"
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CREDS_FILE = REPO_ROOT / "ebay_credentials.json"


def load_credentials_into_env() -> None:
    """Populate EBAY_CREDENTIALS_JSON so the SDK loader picks it up."""
    if not CREDS_FILE.exists():
        sys.exit(f"Credentials file not found: {CREDS_FILE}")
    os.environ["EBAY_CREDENTIALS_JSON"] = CREDS_FILE.read_text()


def get_token() -> str:
    """Use the existing SDK token provider so we don't reimplement OAuth."""
    from ebay_client.auth import EbayTokenProvider
    from ebay_client.browse import EbayBrowseClient
    from ebay_client.config import load_ebay_credentials

    provider = EbayTokenProvider(
        credentials=load_ebay_credentials(),
        token_url=EbayBrowseClient.token_url,
    )
    return provider.get_token()


def search(token: str, keywords: str, fieldgroups: str | None) -> dict:
    """Hit Browse search directly; return parsed JSON."""
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
        "Accept": "application/json",
    }
    params: dict[str, str | int] = {"q": keywords, "limit": 3}
    if fieldgroups:
        params["fieldgroups"] = fieldgroups

    response = requests.get(
        "https://api.ebay.com/buy/browse/v1/item_summary/search",
        headers=headers,
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def keys_of_first_item(payload: dict) -> set[str]:
    items = payload.get("itemSummaries", [])
    if not items:
        return set()
    return set(items[0].keys())


def main() -> None:
    keywords = sys.argv[1] if len(sys.argv) > 1 else "iphone 13"
    load_credentials_into_env()
    token = get_token()

    default_payload = search(token, keywords, fieldgroups=None)
    extended_payload = search(token, keywords, fieldgroups="EXTENDED")

    default_keys = keys_of_first_item(default_payload)
    extended_keys = keys_of_first_item(extended_payload)
    new_keys = sorted(extended_keys - default_keys)

    print(f"Query: {keywords!r}")
    print(f"Default response:  {len(default_keys)} keys on first item")
    print(f"EXTENDED response: {len(extended_keys)} keys on first item")
    print(f"\nKeys ONLY in EXTENDED: {new_keys}")

    first_item = extended_payload.get("itemSummaries", [{}])[0]
    for key in ("shortDescription", "aspects", "localizedAspects"):
        value = first_item.get(key)
        print(f"\n--- {key} ---")
        if value is None:
            print("  (not present)")
            continue
        rendered = json.dumps(value, indent=2, ensure_ascii=False)
        if len(rendered) > 800:
            rendered = rendered[:800] + " ... [truncated]"
        print(rendered)


if __name__ == "__main__":
    main()
