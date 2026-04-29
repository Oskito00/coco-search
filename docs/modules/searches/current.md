# `app/searches/` — Current State

Owns the lifecycle of one scrape pass: define a saved search, ask eBay for
items, persist them, and emit the domain events that downstream layers
(notifications, relevance) consume.

## Entry points

- **`ScheduledQueryService`** — invoked by an RQ worker. One method per
  cadence (`run_full_scrape`, `run_recent_scrape`); each picks a strategy and
  runs the orchestrator.
- **`SearchItemProcessor`** — the orchestrator. Takes raw eBay items + a
  `UserQuery`, writes everything that needs writing, returns a
  `SearchProcessingResult`.
- **`process_items`** — legacy free function preserved for callers that want
  `(new_items, updated_items)`. Internally wraps `SearchItemProcessor`.

## Two scrape strategies

`strategies.py` defines the `ScrapeStrategy` Protocol and two concrete
implementations. The scheduler treats them as opaque.

| Strategy | Purpose | Sort | `max_pages` |
|---|---|---|---|
| `RecentScrapeStrategy` | Cheap, surfaces newly-listed items + auctions ending soon | `newlyListed` | 1 |
| `FullScrapeStrategy` | Catalogue refresh — drives price-drop / state-change detection on known items | eBay default (`bestMatch`) | 5 |

Both call `EbaySearchExecutor` (in `execution.py`), which wraps the
`ebay_client` SDK with a circuit breaker and an after-the-fact
`required_keywords` / `excluded_keywords` filter.

## The orchestrator

`SearchItemProcessor.process(items, query, ...)` walks each raw item through
the same pipeline:

1. `normalize_item_payload` → dict shaped for the DB.
2. **Upsert**: `_create_new` if the eBay id is unseen, otherwise
   `_update_existing` (which also handles the price-drop / item-update events
   and the legacy feedback gate).
3. `ObservationRecorder.record(...)` — one row in `item_observations`.
4. `FeatureSnapshotRecorder.record(...)` — one row in
   `item_feature_snapshots` with raw item + saved-search features (raw-v1).
5. `_track_ending_auction` — emits an `auction_ending_soon` event when the
   listing is inside the 12 h window and the link hasn't already been
   notified.

The orchestrator commits the SQLAlchemy session once at the end and (when
`notify=True`) calls `EventNotificationService.notify_search_events`.

## `processing/` — single-purpose collaborators

```
processing/
  auction.py              is_ending_within(end_time, now, window=12h)
  differ.py               diff_item, detect_price_drop  (pure)
  event_recorder.py       EventRecorder, NoopEventRecorder
  observation_recorder.py ObservationRecorder, NoopObservationRecorder,
                          ObservationContext, build_observation_payload
  feature_recorder.py     FeatureSnapshotRecorder,
                          NoopFeatureSnapshotRecorder,
                          FeatureSnapshotContext (raw-v1)
  serialization.py        serialize_for_persistence (datetime -> ISO 8601)
```

Each collaborator does one thing. The orchestrator composes them in a
predictable order so cyclomatic complexity in any one method stays low.

### Recorder defaults

| Recorder | Default repository | Real model |
|---|---|---|
| `EventRecorder` | `DomainEventRepository` | `DomainEvent` |
| `ObservationRecorder` | `ItemObservationRepository` | `ItemObservation` |
| `FeatureSnapshotRecorder` | `ItemFeatureSnapshotRepository` | `ItemFeatureSnapshot` |

If a test passes a fake repo with the legacy hooks (`record_domain_event`,
`record_item_observation`), the orchestrator still bridges to it. New
production code should always pass a real `create()`-bearing repository
(or accept the defaults).

## Other modules

- `definitions.py` — `SavedSearch`, `SearchFilters`, `SearchSchedule`
  domain dataclasses.
- `mapping.py` — `saved_search_from_model(UserQuery) -> SavedSearch`,
  `to_ebay_search_params(SavedSearch) -> dict`.
- `events.py` — `DomainEvent` dataclass + the four `build_*_event` factories.
- `validation.py` — quota / shape checks before a search is persisted.
- `saved_search_service.py` — CRUD for saved searches; consumed by the API.
- `onboarding.py` — `SearchOnboardingService` (built; no live route exposes
  it yet — kept for the future preview-flow UX).
- `sampling.py` — utilities for the onboarding preview.

## Current package layout

```text
app/searches/
  __init__.py
  definitions.py
  events.py
  execution.py
  item_processor.py
  mapping.py
  onboarding.py
  sampling.py
  saved_search_service.py
  scheduled.py
  strategies.py
  validation.py
  processing/
    __init__.py
    auction.py
    differ.py
    event_recorder.py
    feature_recorder.py
    observation_recorder.py
    serialization.py
```
