import json
from datetime import datetime, timezone

from ebay_client.browse.parsers import parse_item_summary_response


def test_parse_fixed_price_item_summary_response():
    response = {
        "itemSummaries": [
            {
                "itemId": "v1|123|0",
                "legacyItemId": "123",
                "title": "Vintage Camera",
                "price": {"value": "12.50", "currency": "GBP"},
                "buyingOptions": ["FIXED_PRICE"],
                "itemWebUrl": "https://www.ebay.co.uk/itm/123",
                "image": {"imageUrl": "https://i.ebayimg.com/images/123.jpg"},
                "seller": {"username": "camera-shop", "feedbackPercentage": "99.8"},
                "condition": "Used",
                "itemLocation": {"country": "GB", "postalCode": "SW1A"},
                "itemCreationDate": "2026-04-01T10:11:12.000Z",
                "itemEndDate": "2026-04-08T10:11:12.000Z",
                "listingMarketplaceId": "EBAY_GB",
            }
        ]
    }

    item = parse_item_summary_response(response)[0]

    assert item["ebay_id"] == "v1|123|0"
    assert item["legacy_id"] == "123"
    assert item["title"] == "Vintage Camera"
    assert item["price"] == 12.5
    assert item["currency"] == "GBP"
    assert item["current_bid"] == 0
    assert item["current_bid_currency"] == "GBP"
    assert item["auction_details"] is None
    assert item["buying_options"] == json.dumps(["FIXED_PRICE"])
    assert item["start_time"] == datetime(2026, 4, 1, 10, 11, 12, tzinfo=timezone.utc)
    assert item["end_time"] == datetime(2026, 4, 8, 10, 11, 12, tzinfo=timezone.utc)


def test_parse_auction_item_summary_response():
    response = {
        "itemSummaries": [
            {
                "itemId": "v1|auction|0",
                "title": "Rare Record",
                "price": {"value": "20.00", "currency": "GBP"},
                "buyingOptions": ["AUCTION"],
                "bidCount": 7,
                "currentBidPrice": {"value": "44.25", "currency": "USD"},
                "itemEndDate": "2026-05-01T17:30:00.000Z",
                "listingMarketplaceId": "EBAY_US",
            }
        ]
    }

    item = parse_item_summary_response(response)[0]
    auction_details = json.loads(item["auction_details"])

    assert item["price"] == 20.0
    assert item["current_bid"] == 44.25
    assert item["current_bid_currency"] == "USD"
    assert auction_details == {
        "bid_count": 7,
        "current_bid": {"value": 44.25, "currency": "USD"},
        "end_time": "2026-05-01T17:30:00.000Z",
        "marketplace_id": "EBAY_US",
    }


def test_parse_item_summary_response_with_missing_optional_fields():
    response = {
        "itemSummaries": [
            {
                "itemId": "v1|minimal|0",
                "price": {"value": "3.00", "currency": "GBP"},
            }
        ]
    }

    item = parse_item_summary_response(response)[0]

    assert item["title"] == "No Title"
    assert item["image_url"] is None
    assert item["seller"] is None
    assert item["seller_rating"] is None
    assert item["condition"] is None
    assert item["location"] == {"country": None, "postal_code": None}
    assert item["start_time"] is None
    assert item["end_time"] is None
    assert item["buying_options"] == json.dumps([])
    assert item["auction_details"] is None
    assert json.loads(item["categories"]) == {"ids": [], "names": []}
    assert json.loads(item["images"]) == {"main": None, "thumbnails": []}


def test_parse_item_summary_response_with_categories_and_images():
    response = {
        "itemSummaries": [
            {
                "itemId": "v1|media|0",
                "price": {"value": "9.99", "currency": "GBP"},
                "categories": [
                    {"categoryId": "625", "categoryName": "Cameras"},
                    {"categoryId": "31388", "categoryName": "Film Cameras"},
                ],
                "image": {"imageUrl": "https://i.ebayimg.com/images/main.jpg"},
                "thumbnailImages": [
                    {"imageUrl": "https://i.ebayimg.com/images/thumb-1.jpg"},
                    {"imageUrl": "https://i.ebayimg.com/images/thumb-2.jpg"},
                ],
            }
        ]
    }

    item = parse_item_summary_response(response)[0]

    assert json.loads(item["categories"]) == {
        "ids": ["625", "31388"],
        "names": ["Cameras", "Film Cameras"],
    }
    assert json.loads(item["images"]) == {
        "main": "https://i.ebayimg.com/images/main.jpg",
        "thumbnails": [
            "https://i.ebayimg.com/images/thumb-1.jpg",
            "https://i.ebayimg.com/images/thumb-2.jpg",
        ],
    }


def test_parse_item_summary_response_uses_default_currency():
    response = {
        "itemSummaries": [
            {
                "itemId": "v1|default-currency|0",
                "price": {"value": "7.50"},
                "buyingOptions": ["AUCTION"],
                "currentBidPrice": {"value": "8.25"},
            }
        ]
    }

    item = parse_item_summary_response(response, default_currency="EUR")[0]
    auction_details = json.loads(item["auction_details"])

    assert item["currency"] == "EUR"
    assert item["current_bid_currency"] == "EUR"
    assert auction_details["current_bid"] == {"value": 8.25, "currency": "EUR"}
