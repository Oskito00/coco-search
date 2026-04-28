from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Optional

import pytest
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase

from app.repositories._models import RepositoryModelUnavailable
from app.repositories.events import DomainEventRepository
from app.repositories.features import ItemFeatureSnapshotRepository
from app.repositories.interactions import InteractionRepository
from app.repositories.notifications import NotificationRecordRepository
from app.repositories.observations import ItemObservationRepository
from app.repositories.runs import SearchRunRepository


class Base(DeclarativeBase):
    pass


class SearchRun(Base):
    __tablename__ = "test_search_runs"

    search_run_id = Column(BigInteger, primary_key=True)
    query_id = Column(String, nullable=False)
    run_type = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False)
    source = Column(String(50))
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    items_seen = Column(Integer, nullable=False, default=0)
    items_created = Column(Integer, nullable=False, default=0)
    items_updated = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False)


class ItemObservation(Base):
    __tablename__ = "test_item_observations"

    item_observation_id = Column(BigInteger, primary_key=True)
    search_run_id = Column(BigInteger)
    query_id = Column(String, nullable=False)
    item_id = Column(BigInteger, nullable=False)
    observed_at = Column(DateTime, nullable=False)
    price = Column(Numeric(10, 2))
    currency = Column(String(10))
    current_bid = Column(Numeric(10, 2))
    condition = Column(String(50))
    buying_options = Column(String(255))
    listing_status = Column(String(50))
    hard_filter_passed = Column(Boolean)
    is_new_item = Column(Boolean, nullable=False, default=False)
    raw_item_snapshot = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False)


class UserItemInteraction(Base):
    __tablename__ = "test_user_item_interactions"

    user_item_interaction_id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, nullable=False)
    query_id = Column(String)
    item_id = Column(BigInteger, nullable=False)
    interaction_type = Column(String(40), nullable=False)
    label = Column(String(40))
    source = Column(String(50))
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False)


class ItemFeatureSnapshot(Base):
    __tablename__ = "test_item_feature_snapshots"

    item_feature_snapshot_id = Column(BigInteger, primary_key=True)
    query_id = Column(String, nullable=False)
    item_id = Column(BigInteger, nullable=False)
    search_run_id = Column(BigInteger)
    feature_version = Column(String(40), nullable=False)
    model_version = Column(String(80))
    features = Column(JSON, nullable=False, default=dict)
    relevance_score = Column(Float)
    should_notify = Column(Boolean)
    decision = Column(String(40))
    created_at = Column(DateTime, nullable=False)


class DomainEvent(Base):
    __tablename__ = "test_domain_events"

    domain_event_id = Column(BigInteger, primary_key=True)
    event_type = Column(String(80), nullable=False)
    aggregate_type = Column(String(50), nullable=False)
    aggregate_id = Column(String(100), nullable=False)
    user_id = Column(Integer)
    query_id = Column(String)
    item_id = Column(BigInteger)
    status = Column(String(30), nullable=False)
    source = Column(String(50))
    payload = Column(JSON, nullable=False, default=dict)
    occurred_at = Column(DateTime, nullable=False)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False)


class NotificationRecord(Base):
    __tablename__ = "test_notification_records"

    notification_record_id = Column(BigInteger, primary_key=True)
    domain_event_id = Column(BigInteger)
    user_id = Column(Integer, nullable=False)
    query_id = Column(String)
    item_id = Column(BigInteger)
    channel = Column(String(40), nullable=False)
    notification_type = Column(String(60), nullable=False)
    status = Column(String(30), nullable=False)
    recipient = Column(String(255))
    payload = Column(JSON, nullable=False, default=dict)
    error_message = Column(Text)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False)


class CaptureSession:
    def __init__(self) -> None:
        self.records: list[Any] = []
        self.flush_count = 0

    def add(self, record: Any) -> None:
        self.records.append(record)

    def flush(self) -> None:
        self.flush_count += 1

    def get(self, model: Any, record_id: Any) -> Any:
        return SimpleNamespace(keyword_id=99)


class QuerySpy:
    def __init__(self) -> None:
        self.filters: list[dict[str, Any]] = []
        self.limit_value: Optional[int] = None

    def filter_by(self, **filters: Any) -> "QuerySpy":
        self.filters.append(filters)
        return self

    def order_by(self, *args: Any) -> "QuerySpy":
        return self

    def limit(self, value: int) -> "QuerySpy":
        self.limit_value = value
        return self

    def all(self) -> list[str]:
        return ["row"]

    def first(self) -> str:
        return "row"


class FakeFeedbackRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def record(self, **values: object) -> dict[str, object]:
        self.calls.append(values)
        return values


@pytest.mark.parametrize(
    ("repository", "method_name", "args"),
    [
        (SearchRunRepository(session=object()), "create", {"query_id": "query-1"}),
        (
            ItemObservationRepository(session=object()),
            "create",
            {"query_id": "query-1", "item_id": 1},
        ),
        (
            DomainEventRepository(session=object()),
            "create",
            {
                "event_type": "item.matched",
                "aggregate_type": "saved_search",
                "aggregate_id": "query-1",
            },
        ),
        (
            NotificationRecordRepository(session=object()),
            "create",
            {
                "user_id": 1,
                "query_id": "query-1",
                "item_id": 2,
                "notification_type": "new_item",
                "channel": "telegram",
            },
        ),
        (
            ItemFeatureSnapshotRepository(session=object()),
            "create",
            {
                "item_id": 2,
                "query_id": "query-1",
                "features": {"price": 12.5},
            },
        ),
    ],
)
def test_future_schema_repositories_raise_clear_dependency_error(
    repository,
    method_name,
    args,
) -> None:
    with pytest.raises(RepositoryModelUnavailable) as exc_info:
        getattr(repository, method_name)(**args)

    assert repository.model_name in str(exc_info.value)
    assert "schema-worker model" in str(exc_info.value)


def test_search_runs_use_schema_query_columns() -> None:
    session = CaptureSession()
    repository = SearchRunRepository(session=session, model=SearchRun)
    started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    record = repository.create(
        query_id="query-1",
        run_type="scheduled",
        source="scheduler",
        started_at=started_at,
        items_seen=3,
    )
    repository.mark_finished(record, status="failed", error_message="timeout")

    assert record.query_id == "query-1"
    assert record.search_run_id is None
    assert record.error_message == "timeout"
    assert "search_id" not in record.__dict__


def test_search_run_create_maps_search_id_alias_to_query_id() -> None:
    repository = SearchRunRepository(session=CaptureSession(), model=SearchRun)

    record = repository.create(search_id="query-1")

    assert record.query_id == "query-1"
    assert "search_id" not in record.__dict__


def test_search_run_list_filters_by_query_id() -> None:
    query = QuerySpy()
    SearchRun.query = query

    result = SearchRunRepository(session=object(), model=SearchRun).list_recent(
        query_id="query-1", limit=5
    )

    assert result == ["row"]
    assert query.filters == [{"query_id": "query-1"}]
    assert query.limit_value == 5


def test_item_observations_use_schema_snapshot_columns() -> None:
    session = CaptureSession()
    repository = ItemObservationRepository(session=session, model=ItemObservation)

    record = repository.create(
        query_id="query-1",
        search_run_id=7,
        item_id=2,
        raw_item_snapshot={"title": "Camera"},
        hard_filter_passed=True,
        is_new_item=True,
    )

    assert record.query_id == "query-1"
    assert record.search_run_id == 7
    assert record.raw_item_snapshot == {"title": "Camera"}
    assert "run_id" not in record.__dict__
    assert "payload" not in record.__dict__


def test_item_observation_create_maps_legacy_aliases() -> None:
    repository = ItemObservationRepository(
        session=CaptureSession(),
        model=ItemObservation,
    )

    record = repository.create(
        item_id=2,
        search_id="query-1",
        run_id=7,
        payload={"title": "Camera"},
    )

    assert record.query_id == "query-1"
    assert record.search_run_id == 7
    assert record.raw_item_snapshot == {"title": "Camera"}
    assert "search_id" not in record.__dict__
    assert "run_id" not in record.__dict__
    assert "payload" not in record.__dict__


def test_item_observation_list_filters_by_search_run_id() -> None:
    query = QuerySpy()
    ItemObservation.query = query

    result = ItemObservationRepository(
        session=object(), model=ItemObservation
    ).list_for_run(search_run_id=7, limit=10)

    assert result == ["row"]
    assert query.filters == [{"search_run_id": 7}]
    assert query.limit_value == 10


def test_feature_snapshots_use_query_and_run_columns() -> None:
    session = CaptureSession()
    repository = ItemFeatureSnapshotRepository(
        session=session,
        model=ItemFeatureSnapshot,
    )

    record = repository.create(
        query_id="query-1",
        search_run_id=7,
        item_id=2,
        features={"title_similarity": 0.8},
        relevance_score=0.7,
        should_notify=True,
        decision="notify",
    )

    assert record.query_id == "query-1"
    assert record.search_run_id == 7
    assert record.feature_version == "v1"
    assert "search_id" not in record.__dict__


def test_feature_snapshot_create_maps_search_id_alias() -> None:
    repository = ItemFeatureSnapshotRepository(
        session=CaptureSession(),
        model=ItemFeatureSnapshot,
    )

    record = repository.create(
        search_id="query-1",
        item_id=2,
        features={"title_similarity": 0.8},
    )

    assert record.query_id == "query-1"
    assert "search_id" not in record.__dict__


def test_latest_for_search_item_filters_by_query_id() -> None:
    query = QuerySpy()
    ItemFeatureSnapshot.query = query

    result = ItemFeatureSnapshotRepository(
        session=object(), model=ItemFeatureSnapshot
    ).latest_for_search_item(search_id="query-1", item_id=2)

    assert result == "row"
    assert query.filters == [{"query_id": "query-1", "item_id": 2}]


def test_interactions_use_query_id_and_metadata_json() -> None:
    session = CaptureSession()
    repository = InteractionRepository(
        session=session,
        model=UserItemInteraction,
    )

    record = repository.record_interaction(
        user_id=1,
        query_id="query-1",
        item_id=2,
        interaction_type="feedback",
        label="relevant",
        source="details",
        metadata_json={"source_item_rank": 1},
    )

    assert record.query_id == "query-1"
    assert record.metadata_json == {"source_item_rank": 1}
    assert "search_id" not in record.__dict__


def test_interactions_map_search_id_and_metadata_aliases() -> None:
    repository = InteractionRepository(
        session=CaptureSession(),
        model=UserItemInteraction,
    )

    record = repository.record_interaction(
        user_id=1,
        search_id="query-1",
        item_id=2,
        interaction_type="feedback",
        metadata={"source_item_rank": 1},
    )

    assert record.query_id == "query-1"
    assert record.metadata_json == {"source_item_rank": 1}
    assert "search_id" not in record.__dict__
    assert "metadata" not in record.__dict__


def test_interaction_repository_falls_back_to_legacy_feedback() -> None:
    feedback = FakeFeedbackRepository()
    repository = InteractionRepository(
        session=CaptureSession(),
        feedback_repository=feedback,  # type: ignore[arg-type]
    )

    result = repository.record_interaction(
        user_id=1,
        query_id="query-1",
        item_id=2,
        interaction_type="dismissed",
        label=None,
        source="test",
    )

    assert result == {
        "user_id": 1,
        "item_id": 2,
        "keyword_id": 99,
        "is_relevant": False,
    }
    assert feedback.calls == [result]


def test_notification_records_use_error_message_without_failed_at() -> None:
    session = CaptureSession()
    repository = NotificationRecordRepository(
        session=session,
        model=NotificationRecord,
    )

    record = repository.create(
        user_id=1,
        query_id="query-1",
        item_id=2,
        domain_event_id=3,
        notification_type="new_item",
        channel="telegram",
        payload={"title": "Camera"},
    )
    repository.mark_failed(record, error_message="telegram timeout")

    assert record.query_id == "query-1"
    assert record.domain_event_id == 3
    assert record.error_message == "telegram timeout"
    assert "failed_at" not in record.__dict__
    assert "error" not in record.__dict__


def test_notification_records_map_legacy_aliases() -> None:
    repository = NotificationRecordRepository(
        session=CaptureSession(),
        model=NotificationRecord,
    )

    record = repository.create(
        user_id=1,
        search_id="query-1",
        notification_type="new_item",
        channel="telegram",
        metadata={"title": "Camera"},
    )
    repository.mark_failed(record, error="telegram timeout")

    assert record.query_id == "query-1"
    assert record.payload == {"title": "Camera"}
    assert record.error_message == "telegram timeout"
    assert "search_id" not in record.__dict__
    assert "metadata" not in record.__dict__
    assert "error" not in record.__dict__
    assert "failed_at" not in record.__dict__


def test_domain_events_list_pending_unprocessed_events() -> None:
    query = QuerySpy()
    DomainEvent.query = query

    result = DomainEventRepository(
        session=object(), model=DomainEvent
    ).list_unprocessed(limit=25)

    assert result == ["row"]
    assert query.filters == [{"status": "pending", "processed_at": None}]
    assert query.limit_value == 25
