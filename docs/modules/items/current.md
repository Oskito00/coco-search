# `app/items/` — Current State

Helpers that bridge the eBay SDK's response shape and the `Item` SQLAlchemy
model. There is intentionally no business logic here — just shape-mapping.

## `normalization.py`

`normalize_item_payload(raw: dict) -> dict` accepts either:

- A parsed item produced by `ebay_client.browse.parsers` (snake-case keys,
  numeric prices), or
- A raw eBay item-summary payload (camelCase keys, `{"value", "currency"}`
  money objects).

…and produces a flat dict whose keys match `Item` columns. Unset values are
stripped so `Item.create(**payload)` only sets the fields actually present.

### Fields captured (Phase 4 update)

In addition to the original set (title, price, seller, location, images,
buying_options, ...), the parser+normalizer now capture:

| Field | Source | Notes |
|---|---|---|
| `short_description` | `shortDescription` (requires `fieldgroups=EXTENDED`) | ~150-char plain-text snippet |
| `top_rated_seller` | `topRatedBuyingExperience` | Boolean |
| `shipping_cost` | `shippingOptions[0].shippingCost.value` | Numeric |
| `free_shipping` | derived | `cost == 0` or pickup-only |
| `watch_count` | `watchCount` | Sometimes present |
| `image_count` | `1 + len(thumbnailImages)` | Includes the main image |

These values flow straight into the `items` table (Alembic migration
`b2c3d4e5f6a7_item_extended_fields.py`) and into the raw item features in
`app.relevance.features.item`.

## Current package layout

```text
app/items/
  __init__.py
  normalization.py
```
