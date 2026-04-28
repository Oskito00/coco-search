import json

from ebay_client.time import parse_ebay_datetime


def parse_item_summary_response(response, default_currency="GBP"):
    items = []
    for item_data in response.get("itemSummaries", []):
        price_info = item_data.get("price", {})
        base_price = {
            "value": float(price_info.get("value", 0)),
            "currency": price_info.get("currency", default_currency),
        }

        raw_buying_options = item_data.get("buyingOptions", [])
        is_auction = "AUCTION" in raw_buying_options
        auction_data = (
            {
                "bid_count": item_data.get("bidCount", 0),
                "current_bid": {
                    "value": float(item_data.get("currentBidPrice", {}).get("value", 0)),
                    "currency": item_data.get("currentBidPrice", {}).get(
                        "currency", default_currency
                    ),
                },
                "end_time": item_data.get("itemEndDate"),
                "marketplace_id": item_data.get("listingMarketplaceId"),
            }
            if is_auction
            else None
        )

        items.append(
            {
                "ebay_id": item_data.get("itemId"),
                "legacy_id": item_data.get("legacyItemId"),
                "title": item_data.get("title", "No Title"),
                "price": base_price["value"],
                "current_bid": (
                    auction_data["current_bid"]["value"]
                    if auction_data and "current_bid" in auction_data
                    else 0
                ),
                "current_bid_currency": (
                    auction_data["current_bid"]["currency"]
                    if auction_data and "current_bid" in auction_data
                    else base_price.get("currency", default_currency)
                ),
                "currency": base_price["currency"],
                "url": item_data.get("itemWebUrl"),
                "image_url": item_data.get("image", {}).get("imageUrl"),
                "seller": item_data.get("seller", {}).get("username"),
                "seller_rating": item_data.get("seller", {}).get("feedbackPercentage"),
                "condition": item_data.get("condition"),
                "location": {
                    "country": item_data.get("itemLocation", {}).get("country"),
                    "postal_code": item_data.get("itemLocation", {}).get("postalCode"),
                },
                "start_time": parse_ebay_datetime(item_data.get("itemCreationDate")),
                "end_time": parse_ebay_datetime(item_data.get("itemEndDate")),
                "buying_options": json.dumps(raw_buying_options),
                "auction_details": json.dumps(auction_data) if auction_data else None,
                "categories": json.dumps(
                    {
                        "ids": [
                            category["categoryId"]
                            for category in item_data.get("categories", [])
                        ],
                        "names": [
                            category["categoryName"]
                            for category in item_data.get("categories", [])
                        ],
                    }
                ),
                "marketplace": item_data.get("listingMarketplaceId"),
                "images": json.dumps(
                    {
                        "main": item_data.get("image", {}).get("imageUrl"),
                        "thumbnails": [
                            image.get("imageUrl")
                            for image in item_data.get("thumbnailImages", [])
                        ],
                    }
                ),
            }
        )

    return items
