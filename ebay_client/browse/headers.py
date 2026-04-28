from ebay_client.marketplaces import Marketplace


def format_marketplace_header(marketplace: str) -> str:
    """Return the eBay marketplace header value for an internal marketplace code."""
    return marketplace.replace("_", "-")


def build_browse_headers(
    token: str,
    marketplace: str,
    marketplace_config: Marketplace,
) -> dict[str, str]:
    """Build headers required by eBay Browse API search requests."""
    return {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": format_marketplace_header(marketplace),
        "X-EBAY-C-CURRENCY": marketplace_config.currency,
        "Content-Language": marketplace_config.language,
        "Accept-Language": marketplace_config.language,
        "Content-Type": "application/json",
    }
