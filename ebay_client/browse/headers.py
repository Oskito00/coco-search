"""Header helpers for eBay Browse API requests."""


def build_browse_headers(
    *,
    token: str,
    marketplace: str,
    currency: str,
    language: str,
) -> dict[str, str]:
    """Build headers shared by Browse API calls."""
    marketplace_header = marketplace.replace("_", "-")
    return {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": marketplace_header,
        "X-EBAY-C-CURRENCY": currency,
        "Content-Language": language,
        "Accept-Language": language,
        "Content-Type": "application/json",
    }
