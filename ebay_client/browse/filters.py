from ebay_client.browse.dto import SearchFilters


class SearchFilterBuilder:
    def __init__(self, currency):
        self.currency = currency

    def build(self, filters):
        filters = SearchFilters.from_mapping(filters) if isinstance(filters, dict) else filters
        filter_parts = []

        item_location = filters.item_location
        if item_location and item_location != "any":
            filter_parts.append(f"itemLocationCountry:{item_location}")

        if filters.buying_options != "FIXED_PRICE|AUCTION":
            filter_parts.append(f"buyingOptions:{{{filters.buying_options}}}")

        if filters.condition in ["NEW", "USED"]:
            filter_parts.append(f"conditions:{{{filters.condition}}}")

        if filters.min_price or filters.max_price:
            filter_parts.append(f"priceCurrency:{self.currency}")

        if filters.min_price is not None or filters.max_price is not None:
            if filters.min_price is not None and filters.max_price is not None:
                price_range = f"{filters.min_price}..{filters.max_price}"
            elif filters.min_price is not None:
                price_range = f"{filters.min_price}.."
            else:
                price_range = f"..{filters.max_price}"
            filter_parts.append(f"price:[{price_range}]")

        return ",".join(filter_parts)


def build_search_filter(filters, currency):
    return SearchFilterBuilder(currency).build(filters)
