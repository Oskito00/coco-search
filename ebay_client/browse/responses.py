def dedupe_items(items):
    seen_ids = set()
    unique_items = []
    for item in items:
        item_id = item.get("ebay_id")
        if item_id:
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                unique_items.append(item)
        else:
            unique_items.append(item)
    return unique_items
