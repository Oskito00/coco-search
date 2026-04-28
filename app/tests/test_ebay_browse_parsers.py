import json
from datetime import datetime, timezone

from ebay_client.browse.parsers import parse_item_summary_response


def test_parse_fixed_price_item_summary_response() -> None:
    response = {
        "itemSummaries": [
            {
                "itemId": "v1|123|0",
                "legacyItemId": "123",
                "title": "Pokemon Booster Box",
                "price": {"value": "149.99", "currency": "GBP"},
                "buyingOptions": ["FIXED_PRICE"],
                "itemWebUrl": "https://www.ebay.co.uk/itm/123",
                "image": {"imageUrl": "https://i.ebayimg.com/main.jpg"},
                "seller": {"username": "cardseller", "feedbackPercentage": "99.8"},
                "condition": "New",
                "itemLocation": {"country": "GB", "postalCode": "SW1A"},
                "itemCreationDate": "2026-04-01T10:30:00.000Z",
                "itemEndDate": "2026-04-30T10:30:00.000Z",
                "listingMarketplaceId": "EBAY_GB",
            }
        ]
    }

    item = parse_item_summary_response(response)[0]

    assert item["ebay_id"] == "v1|123|0"
    assert item["legacy_id"] == "123"
    assert item["title"] == "Pokemon Booster Box"
    assert item["price"] == 149.99
    assert item["currency"] == "GBP"
    assert item["current_bid"] == 0.0
    assert item["current_bid_currency"] == "GBP"
    assert item["url"] == "https://www.ebay.co.uk/itm/123"
    assert item["image_url"] == "https://i.ebayimg.com/main.jpg"
    assert item["seller"] == "cardseller"
    assert item["seller_rating"] == "99.8"
    assert item["condition"] == "New"
    assert item["location"] == {"country": "GB", "postal_code": "SW1A"}
    assert item["start_time"] == datetime(2026, 4, 1, 10, 30, tzinfo=timezone.utc)
    assert item["end_time"] == datetime(2026, 4, 30, 10, 30, tzinfo=timezone.utc)
    assert json.loads(item["buying_options"]) == ["FIXED_PRICE"]
    assert item["auction_details"] is None
    assert item["marketplace"] == "EBAY_GB"


def test_parse_auction_item_summary_response() -> None:
    response = {
        "itemSummaries": [
            {
                "itemId": "v1|456|0",
                "title": "Auction Card",
                "price": {"value": "10.00", "currency": "GBP"},
                "currentBidPrice": {"value": "22.50", "currency": "GBP"},
                "bidCount": 7,
                "buyingOptions": ["AUCTION"],
                "itemEndDate": "2026-05-01T20:00:00.000Z",
                "listingMarketplaceId": "EBAY_GB",
            }
        ]
    }

    item = parse_item_summary_response(response)[0]
    auction_details = json.loads(item["auction_details"])

    assert item["current_bid"] == 22.5
    assert item["current_bid_currency"] == "GBP"
    assert auction_details == {
        "bid_count": 7,
        "current_bid": {"value": 22.5, "currency": "GBP"},
        "end_time": "2026-05-01T20:00:00.000Z",
        "marketplace_id": "EBAY_GB",
    }


def test_parse_item_summary_response_handles_missing_optional_fields() -> None:
    response = {"itemSummaries": [{"itemId": "v1|789|0"}]}

    item = parse_item_summary_response(response)[0]

    assert item["title"] == "No Title"
    assert item["price"] == 0.0
    assert item["currency"] == "GBP"
    assert item["current_bid"] == 0.0
    assert item["current_bid_currency"] == "GBP"
    assert item["image_url"] is None
    assert item["seller"] is None
    assert item["seller_rating"] is None
    assert item["location"] == {"country": None, "postal_code": None}
    assert item["start_time"] is None
    assert item["end_time"] is None
    assert json.loads(item["buying_options"]) == []
    assert item["auction_details"] is None
    assert json.loads(item["categories"]) == {"ids": [], "names": []}
    assert json.loads(item["images"]) == {"main": None, "thumbnails": []}


def test_parse_item_summary_response_serializes_categories_and_images() -> None:
    response = {
        "itemSummaries": [
            {
                "categories": [
                    {"categoryId": "183454", "categoryName": "CCG Sealed Boxes"},
                    {"categoryId": "261328", "categoryName": "Pokemon Boxes"},
                ],
                "image": {"imageUrl": "https://i.ebayimg.com/main.jpg"},
                "thumbnailImages": [
                    {"imageUrl": "https://i.ebayimg.com/thumb-1.jpg"},
                    {"imageUrl": "https://i.ebayimg.com/thumb-2.jpg"},
                ],
            }
        ]
    }

    item = parse_item_summary_response(response)[0]

    assert json.loads(item["categories"]) == {
        "ids": ["183454", "261328"],
        "names": ["CCG Sealed Boxes", "Pokemon Boxes"],
    }
    assert json.loads(item["images"]) == {
        "main": "https://i.ebayimg.com/main.jpg",
        "thumbnails": [
            "https://i.ebayimg.com/thumb-1.jpg",
            "https://i.ebayimg.com/thumb-2.jpg",
        ],
    }


def test_parse_item_summary_response_uses_default_currency() -> None:
    response = {
        "itemSummaries": [
            {
                "price": {"value": "19.99"},
                "currentBidPrice": {"value": "24.50"},
                "buyingOptions": ["AUCTION"],
            }
        ]
    }

    item = parse_item_summary_response(response, default_currency="EUR")[0]
    auction_details = json.loads(item["auction_details"])

    assert item["currency"] == "EUR"
    assert item["current_bid_currency"] == "EUR"
    assert auction_details["current_bid"]["currency"] == "EUR"
