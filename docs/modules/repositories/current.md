# `app/repositories/` — Current State

Thin wrappers around the SQLAlchemy models. Every repository:

- Accepts an injectable `session` (defaults to `db.session`).
- Exposes a small surface — usually `get`, `create`, `update`, plus a few
  table-specific finders.
- Returns ORM rows (not DTOs). Domain conversion happens in the layer above.

The boundary contract is simple: **the recorders / services in
`app.searches` and `app.notifications` only ever talk to repositories,
never to `db.session` directly.**

## Repositories by aggregate

| File | Repositories | Backing model(s) |
|---|---|---|
| `items.py` | `ItemRepository` (facade), `GlobalItemRepository`, `KeywordItemLinkRepository`, `SearchItemLinkRepository`, `ItemFeedbackRepository` | `Item`, `KeywordItems`, `UserQueryItems`, `ItemRelevanceFeedback` |
| `queries.py` | `UserQueryRepository`, `KeywordRepository` | `UserQuery`, `Keyword` |
| `events.py` | `DomainEventRepository` | `DomainEvent` |
| `observations.py` | `ItemObservationRepository` | `ItemObservation` |
| `runs.py` | `SearchRunRepository` | `SearchRun` |
| `notifications.py` | `NotificationRecordRepository` | `NotificationRecord` |
| `interactions.py` | `InteractionRepository`, `FeedbackRepository` | `UserItemInteraction`, `ItemRelevanceFeedback` |
| `features.py` | `ItemFeatureSnapshotRepository` | `ItemFeatureSnapshot` |

## Optional-model base class

Several aggregates landed in tracked schema migrations after the rest of the
code (`DomainEvent`, `ItemObservation`, `SearchRun`,
`ItemFeatureSnapshot`, `NotificationRecord`, `UserItemInteraction`,
`ItemRelevanceFeedback`). Their repositories extend
`OptionalModelRepository` (`_optional.py`):

- The repository is constructable without the model present.
- Reading the `model` property when the model is missing raises
  `RepositoryModelUnavailable` so the failure is loud and clear.

This lets the rest of the app keep importing repositories during partial
checkouts; only the methods that *write* are gated.

`_models.py` provides shared helpers used by both groups of repositories
(`default_session`, `optional_model`, `require_model`, `model_columns`,
`compact_values`, `create_model`, `update_model`).

## Currently consumed by

- `app.searches.processing.event_recorder.EventRecorder`
- `app.searches.processing.observation_recorder.ObservationRecorder`
- `app.searches.processing.feature_recorder.FeatureSnapshotRecorder`
- `app.searches.scheduled.ScheduledQueryService` (queries)
- `app.notifications.records.NotificationRecordCreator`
- `app.relevance.repository.SqlAlchemyRelevanceRepository` (interactions +
  feedback)

## Current package layout

```text
app/repositories/
  __init__.py
  _models.py           (shared helpers)
  _optional.py         (OptionalModelRepository base)
  events.py
  features.py
  interactions.py
  items.py
  notifications.py
  observations.py
  queries.py
  runs.py
```
