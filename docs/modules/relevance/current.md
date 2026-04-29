# `app/relevance/` — Current State

The relevance layer decides whether an item is worth notifying a user about,
and owns the data that future ML / heuristic scorers will train on.

The live decision path is intentionally **simple**: hard filters → scorer.
The default scorer is `PassThroughScorer` (notify everything). The real ML
work plugs into one well-defined seam.

## Pipeline

```python
RelevanceService.should_notify(user_id, saved_search, item)
  features = FeatureExtractor.extract(saved_search, item)   # legacy combined extractor
  if HardFilter.fails(features): return Reject
  return Scorer.score_features(features)                    # <- the seam
```

## The seam: `Scorer`

`scoring.py` exposes:

- `RelevanceScorer` (Protocol) — the contract every scorer implements.
- `PassThroughScorer` — **default**. Returns `should_notify=True` for
  anything past hard filters. Reasons: `("pass_through",)`.
- `BaselineRelevanceScorer` — the original heuristic. Still around; can be
  injected explicitly.

To plug in an ML model, implement `RelevanceScorer.score_features` and pass
it into `RelevanceService(scorer=...)`. Nothing else changes.

## Features

### Two flavours

`features/` is a package, not a single file:

| File | Purpose |
|---|---|
| `features/item.py` | **Raw** item-only features (no saved-search context). One flat dict per item. |
| `features/search.py` | **Raw** saved-search features. One flat dict per `SavedSearch`. |
| `features/legacy.py` | The original combined extractor used by `BaselineRelevanceScorer` and the in-tree `_hard_filter_failures`. Kept for backwards compatibility. |

### Raw item features (`extract_raw_item_features`)

`price`, `currency`, `condition`, `buying_options`, `has_auction`,
`has_fixed_price`, `seller_feedback_pct`, `top_rated_seller`,
`shipping_cost`, `free_shipping`, `location_country`, `end_time`,
`current_bid`, `title`, `title_length`, `title_word_count`,
`title_has_emoji`, `short_description`, `short_description_length`,
`categories`, `image_count`, `watch_count`, `listing_age_seconds`,
`marketplace`.

### Raw search features (`extract_raw_search_features`)

`keywords`, `min_price`, `max_price`, `condition_filter`,
`location_filter`, `buying_options_filter`, `required_keywords`,
`excluded_keywords`, `marketplace`, `check_interval`.

## Persisted snapshots

Every processed item produces one `ItemFeatureSnapshot` row written by
`FeatureSnapshotRecorder` (`app/searches/processing/feature_recorder.py`).
The JSONB `features` column stores:

```json
{
  "item":   { ...raw item features... },
  "search": { ...raw search features... }
}
```

The version label is `feature_version="raw-v1"`. Future scorers consume this
table directly — no separate ETL needed.

## What's deliberately *not* in the live path

- **Legacy `ItemRelevanceFeedback` thumbs-up/down**. The `_feedback_decision`
  branch was removed from `RelevanceService.should_notify`. The table still
  exists; no live code reads it. Future training datasets should derive
  signal from `UserItemInteraction` instead.
- **Match features (item × search comparisons)**. Today the
  `BaselineRelevanceScorer` still computes some of these inside its scoring
  function (via `legacy.extract_item_features`). New scorers can compose
  match features from the raw snapshot dicts, but they are not stored as a
  separate feature module yet.
- **Onboarding labels** for ML training. Out of scope for now.

## Files of interest

- `service.py` — `RelevanceService` facade. Hard filters + scorer. Records
  interactions through `RelevanceRepository`.
- `domain.py` — `RelevanceDecision` (score, should_notify, reasons,
  features) + `RelevanceInteraction`.
- `repository.py` — `RelevanceRepository` Protocol +
  `SqlAlchemyRelevanceRepository`.
- `feedback.py` — small helpers for the legacy thumbs-up/down API surface.

## Current package layout

```text
app/relevance/
  __init__.py
  domain.py
  feedback.py
  repository.py
  scoring.py                   (RelevanceScorer, PassThroughScorer, BaselineRelevanceScorer)
  service.py                   (RelevanceService)
  features/
    __init__.py
    item.py                    (extract_raw_item_features)
    search.py                  (extract_raw_search_features)
    legacy.py                  (extract_item_features — combined; for the heuristic scorer)
```
