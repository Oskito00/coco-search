"""Add search history, interaction, event, and notification tables.

Revision ID: 6f2a9c1b8d7e
Revises: 79e5d4e6caa5
Create Date: 2026-04-28 15:25:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "6f2a9c1b8d7e"
down_revision = "79e5d4e6caa5"
branch_labels = None
depends_on = None


JSON_DOCUMENT = postgresql.JSONB(astext_type=sa.Text()).with_variant(
    sa.JSON(), "sqlite"
)


def upgrade():
    op.create_table(
        "search_runs",
        sa.Column("search_run_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("query_id", sa.UUID(), nullable=False),
        sa.Column("run_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("items_seen", sa.Integer(), nullable=False),
        sa.Column("items_created", sa.Integer(), nullable=False),
        sa.Column("items_updated", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", JSON_DOCUMENT, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["query_id"], ["user_queries.query_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("search_run_id"),
    )
    op.create_index("ix_search_runs_query_id", "search_runs", ["query_id"])
    op.create_index("ix_search_runs_status", "search_runs", ["status"])
    op.create_index(
        "ix_search_runs_query_started_at", "search_runs", ["query_id", "started_at"]
    )

    op.create_table(
        "item_observations",
        sa.Column(
            "item_observation_id", sa.BigInteger(), autoincrement=True, nullable=False
        ),
        sa.Column("search_run_id", sa.BigInteger(), nullable=True),
        sa.Column("query_id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("current_bid", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("condition", sa.String(length=50), nullable=True),
        sa.Column("buying_options", sa.String(length=255), nullable=True),
        sa.Column("listing_status", sa.String(length=50), nullable=True),
        sa.Column("hard_filter_passed", sa.Boolean(), nullable=True),
        sa.Column("is_new_item", sa.Boolean(), nullable=False),
        sa.Column("raw_item_snapshot", JSON_DOCUMENT, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.item_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["query_id"], ["user_queries.query_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["search_run_id"], ["search_runs.search_run_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("item_observation_id"),
        sa.UniqueConstraint(
            "search_run_id", "item_id", name="uq_item_observations_run_item"
        ),
    )
    op.create_index(
        "ix_item_observations_search_run_id", "item_observations", ["search_run_id"]
    )
    op.create_index("ix_item_observations_query_id", "item_observations", ["query_id"])
    op.create_index("ix_item_observations_item_id", "item_observations", ["item_id"])
    op.create_index(
        "ix_item_observations_query_item_observed_at",
        "item_observations",
        ["query_id", "item_id", "observed_at"],
    )

    op.create_table(
        "user_item_interactions",
        sa.Column(
            "user_item_interaction_id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query_id", sa.UUID(), nullable=True),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("interaction_type", sa.String(length=40), nullable=False),
        sa.Column("label", sa.String(length=40), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("metadata_json", JSON_DOCUMENT, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.item_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["query_id"], ["user_queries.query_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_item_interaction_id"),
    )
    op.create_index(
        "ix_user_item_interactions_interaction_type",
        "user_item_interactions",
        ["interaction_type"],
    )
    op.create_index(
        "ix_user_item_interactions_item_id", "user_item_interactions", ["item_id"]
    )
    op.create_index(
        "ix_user_item_interactions_query_id", "user_item_interactions", ["query_id"]
    )
    op.create_index(
        "ix_user_item_interactions_user_id", "user_item_interactions", ["user_id"]
    )
    op.create_index(
        "ix_user_item_interactions_user_item_created_at",
        "user_item_interactions",
        ["user_id", "item_id", "created_at"],
    )

    op.create_table(
        "item_feature_snapshots",
        sa.Column(
            "item_feature_snapshot_id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("query_id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("search_run_id", sa.BigInteger(), nullable=True),
        sa.Column("feature_version", sa.String(length=40), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=True),
        sa.Column("features", JSON_DOCUMENT, nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("should_notify", sa.Boolean(), nullable=True),
        sa.Column("decision", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.item_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["query_id"], ["user_queries.query_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["search_run_id"], ["search_runs.search_run_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("item_feature_snapshot_id"),
    )
    op.create_index(
        "ix_item_feature_snapshots_item_id", "item_feature_snapshots", ["item_id"]
    )
    op.create_index(
        "ix_item_feature_snapshots_query_id", "item_feature_snapshots", ["query_id"]
    )
    op.create_index(
        "ix_item_feature_snapshots_search_run_id",
        "item_feature_snapshots",
        ["search_run_id"],
    )
    op.create_index(
        "ix_item_feature_snapshots_query_item_created_at",
        "item_feature_snapshots",
        ["query_id", "item_id", "created_at"],
    )

    op.create_table(
        "domain_events",
        sa.Column(
            "domain_event_id", sa.BigInteger(), autoincrement=True, nullable=False
        ),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("aggregate_type", sa.String(length=50), nullable=False),
        sa.Column("aggregate_id", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("query_id", sa.UUID(), nullable=True),
        sa.Column("item_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("payload", JSON_DOCUMENT, nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.item_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["query_id"], ["user_queries.query_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("domain_event_id"),
    )
    op.create_index("ix_domain_events_event_type", "domain_events", ["event_type"])
    op.create_index("ix_domain_events_status", "domain_events", ["status"])
    op.create_index(
        "ix_domain_events_status_occurred_at",
        "domain_events",
        ["status", "occurred_at"],
    )

    op.create_table(
        "notification_records",
        sa.Column(
            "notification_record_id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("domain_event_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query_id", sa.UUID(), nullable=True),
        sa.Column("item_id", sa.BigInteger(), nullable=True),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("notification_type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=True),
        sa.Column("payload", JSON_DOCUMENT, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["domain_event_id"], ["domain_events.domain_event_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.item_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["query_id"], ["user_queries.query_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("notification_record_id"),
    )
    op.create_index(
        "ix_notification_records_domain_event_id",
        "notification_records",
        ["domain_event_id"],
    )
    op.create_index(
        "ix_notification_records_item_id", "notification_records", ["item_id"]
    )
    op.create_index(
        "ix_notification_records_query_id", "notification_records", ["query_id"]
    )
    op.create_index(
        "ix_notification_records_status", "notification_records", ["status"]
    )
    op.create_index(
        "ix_notification_records_user_id", "notification_records", ["user_id"]
    )
    op.create_index(
        "ix_notification_records_user_status_created_at",
        "notification_records",
        ["user_id", "status", "created_at"],
    )


def downgrade():
    op.drop_index(
        "ix_notification_records_user_status_created_at",
        table_name="notification_records",
    )
    op.drop_index("ix_notification_records_user_id", table_name="notification_records")
    op.drop_index("ix_notification_records_status", table_name="notification_records")
    op.drop_index("ix_notification_records_query_id", table_name="notification_records")
    op.drop_index("ix_notification_records_item_id", table_name="notification_records")
    op.drop_index(
        "ix_notification_records_domain_event_id", table_name="notification_records"
    )
    op.drop_table("notification_records")

    op.drop_index("ix_domain_events_status_occurred_at", table_name="domain_events")
    op.drop_index("ix_domain_events_status", table_name="domain_events")
    op.drop_index("ix_domain_events_event_type", table_name="domain_events")
    op.drop_table("domain_events")

    op.drop_index(
        "ix_item_feature_snapshots_query_item_created_at",
        table_name="item_feature_snapshots",
    )
    op.drop_index(
        "ix_item_feature_snapshots_search_run_id", table_name="item_feature_snapshots"
    )
    op.drop_index(
        "ix_item_feature_snapshots_query_id", table_name="item_feature_snapshots"
    )
    op.drop_index(
        "ix_item_feature_snapshots_item_id", table_name="item_feature_snapshots"
    )
    op.drop_table("item_feature_snapshots")

    op.drop_index(
        "ix_user_item_interactions_user_item_created_at",
        table_name="user_item_interactions",
    )
    op.drop_index(
        "ix_user_item_interactions_user_id", table_name="user_item_interactions"
    )
    op.drop_index(
        "ix_user_item_interactions_query_id", table_name="user_item_interactions"
    )
    op.drop_index(
        "ix_user_item_interactions_item_id", table_name="user_item_interactions"
    )
    op.drop_index(
        "ix_user_item_interactions_interaction_type",
        table_name="user_item_interactions",
    )
    op.drop_table("user_item_interactions")

    op.drop_index(
        "ix_item_observations_query_item_observed_at", table_name="item_observations"
    )
    op.drop_index("ix_item_observations_item_id", table_name="item_observations")
    op.drop_index("ix_item_observations_query_id", table_name="item_observations")
    op.drop_index("ix_item_observations_search_run_id", table_name="item_observations")
    op.drop_table("item_observations")

    op.drop_index("ix_search_runs_query_started_at", table_name="search_runs")
    op.drop_index("ix_search_runs_status", table_name="search_runs")
    op.drop_index("ix_search_runs_query_id", table_name="search_runs")
    op.drop_table("search_runs")
