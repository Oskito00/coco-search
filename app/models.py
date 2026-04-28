from datetime import datetime, timezone
import os
import uuid
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import NUMERIC, UUID
from sqlalchemy import JSON, text
from sqlalchemy.dialects.postgresql import JSONB


#For some reason with

JSON_DOCUMENT = JSONB().with_variant(db.JSON(), 'sqlite')


class TimestampMixin:
    """Shared timestamp columns for additive event and history tables."""

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class APSchedulerJob(db.Model):
    __tablename__ = 'apscheduler_jobs'
    id = db.Column(db.String(191), primary_key=True)
    next_run_time = db.Column(db.Float)
    job_state = db.Column(db.LargeBinary)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)

    email_verified = db.Column(db.Boolean, default=False)
    email_verified_on = db.Column(db.DateTime)

    password_hash = db.Column(db.String(256))
    telegram_chat_ids = db.Column(JSONB().with_variant(
        db.JSON(), 'sqlite'
    ), default={'main': None, 'additional': []})
    telegram_connected = db.Column(db.Boolean, default=False)
    telegram_notifications_enabled = db.Column(db.Boolean, default=True)
    notification_preferences = db.Column(JSONB().with_variant(
        db.JSON(), 'sqlite'
    ), default={'price_drops': True, 'new_items': True, 'auction_alerts': True})
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    query_usage = db.Column(db.Integer, default=0)

    # Stripe/Subscription
    stripe_customer_id = db.Column(db.String(50), index=True)
    stripe_subscription_id = db.Column(db.String(50), index=True)
    tier = db.Column(JSONB().with_variant(
        db.JSON(), 'sqlite'
    ), default={'name': 'free', 'query_limit': 0})
    subscription_status = db.Column(db.String(20), default='inactive')  # active/past_due/canceled/expired
    current_period_end = db.Column(db.DateTime)
    requested_change = db.Column(JSONB().with_variant(
        db.JSON(), 'sqlite'
    ))
    pending_tier = db.Column(JSONB().with_variant(
        db.JSON(), 'sqlite'
    ))
    pending_effective_date = db.Column(db.DateTime)
    cancellation_requested = db.Column(db.Boolean, default=False)
    last_checkout_session_id = db.Column(db.String(100))
    grace_period_end = db.Column(db.DateTime)
    payment_failure_start = db.Column(db.DateTime)

    def get_id(self):
        return str(self.id)
        
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class ApiToken(db.Model):
    """Bearer tokens for API access. Stores SHA-256 hash, never the raw token."""

    __tablename__ = 'api_tokens'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(80), nullable=False)
    token_prefix = db.Column(db.String(12), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    scopes = db.Column(JSON_DOCUMENT, default=list, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    revoked_at = db.Column(db.DateTime)

    user = db.relationship('User', backref='api_tokens')


class Item(db.Model):
    __tablename__ = 'items'
    item_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    ebay_id = db.Column(db.String(50), unique=True, nullable=False)
    legacy_id = db.Column(db.String(50))
    title = db.Column(db.String(255))
    price = db.Column(db.Float)
    current_bid = db.Column(db.Float)
    current_bid_currency = db.Column(db.String(10))
    currency = db.Column(db.String(10), default='GBP')
    url = db.Column(db.String(512))
    image_url = db.Column(db.String(255))
    seller = db.Column(db.String(100))
    seller_rating = db.Column(db.String(20))
    condition = db.Column(db.String(50))
    location_country = db.Column(db.String(2)) 
    postal_code = db.Column(db.String(10))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    buying_options = db.Column(db.Text)
    auction_details = db.Column(db.Text)
    categories = db.Column(db.Text)
    marketplace = db.Column(db.String(20))
    images = db.Column(db.Text)
    last_updated = db.Column(db.DateTime)
    
class UserQueryItems(db.Model):
    __tablename__ = 'user_query_items'
    query_id = db.Column(
        UUID(as_uuid=True),  # Must match exactly
        db.ForeignKey('user_queries.query_id', ondelete='CASCADE'),
        primary_key=True
    )
    item_id = db.Column(db.BigInteger, db.ForeignKey('items.item_id'), primary_key=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    auction_ending_notification_sent = db.Column(db.Boolean, default=False)

    #Relationship to UserQuery
    user_query = db.relationship('UserQuery', backref='user_query_items', lazy='joined')

    #Relationship to Item
    item = db.relationship('Item', backref='query_associations', lazy='joined')

class UserQuery(db.Model):
    __tablename__ = 'user_queries'
    query_id = db.Column(
        UUID(as_uuid=True),  # Always use UUID type
        primary_key=True,
        default=uuid.uuid4,
        server_default=text('gen_random_uuid()') if os.environ.get('DYNO') else None
    )
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    keyword_id = db.Column(db.Integer, db.ForeignKey('keywords.keyword_id'), nullable=False)
    keyword = db.relationship('Keyword', backref='user_queries')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Scheduling/operational
    check_interval = db.Column(db.Integer, default=5)  # Default: 5 minutes
    marketplace = db.Column(db.String(10), default='EBAY_GB')
    item_location = db.Column(db.String(10), default='GB')
    last_full_run = db.Column(db.DateTime)
    next_full_run = db.Column(db.DateTime)
    last_recent_run = db.Column(db.DateTime)

    # Critical filters (indexed)
    min_price = db.Column(db.Numeric(10, 2), index=True)
    max_price = db.Column(db.Numeric(10, 2), index=True)
    condition = db.Column(db.String(50), index=True)
    item_location = db.Column(db.String(50), index=True)
    required_keywords = db.Column(db.String(255), index=True)
    excluded_keywords = db.Column(db.String(255), index=True)
    buying_options = db.Column(db.String(255), index=True)
    first_run = db.Column(db.Boolean, default=True)

    # Relevance average score
    average_relevance_score = db.Column(db.Float, default=0.3)

class SearchRun(TimestampMixin, db.Model):
    """Execution history for a saved user query."""

    __tablename__ = 'search_runs'

    search_run_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    query_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('user_queries.query_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    run_type = db.Column(db.String(30), nullable=False, default='scheduled')
    status = db.Column(db.String(30), nullable=False, default='started', index=True)
    source = db.Column(db.String(50))
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finished_at = db.Column(db.DateTime)
    items_seen = db.Column(db.Integer, default=0, nullable=False)
    items_created = db.Column(db.Integer, default=0, nullable=False)
    items_updated = db.Column(db.Integer, default=0, nullable=False)
    error_message = db.Column(db.Text)
    metadata_json = db.Column(JSON_DOCUMENT, default=dict, nullable=False)

    user_query = db.relationship('UserQuery', backref='search_runs')


class ItemObservation(TimestampMixin, db.Model):
    """Search-specific snapshot of an item seen during execution."""

    __tablename__ = 'item_observations'

    item_observation_id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )
    search_run_id = db.Column(
        db.BigInteger,
        db.ForeignKey('search_runs.search_run_id', ondelete='SET NULL'),
        index=True
    )
    query_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('user_queries.query_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    item_id = db.Column(
        db.BigInteger,
        db.ForeignKey('items.item_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    observed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(10))
    current_bid = db.Column(db.Numeric(10, 2))
    condition = db.Column(db.String(50))
    buying_options = db.Column(db.String(255))
    listing_status = db.Column(db.String(50))
    hard_filter_passed = db.Column(db.Boolean)
    is_new_item = db.Column(db.Boolean, default=False, nullable=False)
    raw_item_snapshot = db.Column(JSON_DOCUMENT, default=dict, nullable=False)

    search_run = db.relationship('SearchRun', backref='item_observations')
    user_query = db.relationship('UserQuery', backref='item_observations')
    item = db.relationship('Item', backref='observations')

    __table_args__ = (
        db.UniqueConstraint(
            'search_run_id',
            'item_id',
            name='uq_item_observations_run_item'
        ),
    )


class UserItemInteraction(TimestampMixin, db.Model):
    """User feedback or behavior tied to an item and optional query context."""

    __tablename__ = 'user_item_interactions'

    user_item_interaction_id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    query_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('user_queries.query_id', ondelete='SET NULL'),
        index=True
    )
    item_id = db.Column(
        db.BigInteger,
        db.ForeignKey('items.item_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    interaction_type = db.Column(db.String(40), nullable=False, index=True)
    label = db.Column(db.String(40))
    source = db.Column(db.String(50))
    metadata_json = db.Column(JSON_DOCUMENT, default=dict, nullable=False)

    user = db.relationship('User', backref='item_interactions')
    user_query = db.relationship('UserQuery', backref='item_interactions')
    item = db.relationship('Item', backref='user_interactions')


class ItemFeatureSnapshot(TimestampMixin, db.Model):
    """Versioned relevance features extracted for an item/query pair."""

    __tablename__ = 'item_feature_snapshots'

    item_feature_snapshot_id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )
    query_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('user_queries.query_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    item_id = db.Column(
        db.BigInteger,
        db.ForeignKey('items.item_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    search_run_id = db.Column(
        db.BigInteger,
        db.ForeignKey('search_runs.search_run_id', ondelete='SET NULL'),
        index=True
    )
    feature_version = db.Column(db.String(40), nullable=False, default='v1')
    model_version = db.Column(db.String(80))
    features = db.Column(JSON_DOCUMENT, default=dict, nullable=False)
    relevance_score = db.Column(db.Float)
    should_notify = db.Column(db.Boolean)
    decision = db.Column(db.String(40))

    user_query = db.relationship('UserQuery', backref='feature_snapshots')
    item = db.relationship('Item', backref='feature_snapshots')
    search_run = db.relationship('SearchRun', backref='feature_snapshots')


class DomainEvent(TimestampMixin, db.Model):
    """Durable domain event for downstream notification processing."""

    __tablename__ = 'domain_events'

    domain_event_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    event_type = db.Column(db.String(80), nullable=False, index=True)
    aggregate_type = db.Column(db.String(50), nullable=False)
    aggregate_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    query_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('user_queries.query_id', ondelete='SET NULL')
    )
    item_id = db.Column(
        db.BigInteger,
        db.ForeignKey('items.item_id', ondelete='SET NULL')
    )
    status = db.Column(db.String(30), nullable=False, default='pending', index=True)
    source = db.Column(db.String(50))
    payload = db.Column(JSON_DOCUMENT, default=dict, nullable=False)
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processed_at = db.Column(db.DateTime)

    user = db.relationship('User', backref='domain_events')
    user_query = db.relationship('UserQuery', backref='domain_events')
    item = db.relationship('Item', backref='domain_events')


class NotificationRecord(TimestampMixin, db.Model):
    """Delivery audit trail for notifications emitted from domain events."""

    __tablename__ = 'notification_records'

    notification_record_id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )
    domain_event_id = db.Column(
        db.BigInteger,
        db.ForeignKey('domain_events.domain_event_id', ondelete='SET NULL'),
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    query_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('user_queries.query_id', ondelete='SET NULL'),
        index=True
    )
    item_id = db.Column(
        db.BigInteger,
        db.ForeignKey('items.item_id', ondelete='SET NULL'),
        index=True
    )
    channel = db.Column(db.String(40), nullable=False)
    notification_type = db.Column(db.String(60), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='pending', index=True)
    recipient = db.Column(db.String(255))
    payload = db.Column(JSON_DOCUMENT, default=dict, nullable=False)
    error_message = db.Column(db.Text)
    sent_at = db.Column(db.DateTime)

    domain_event = db.relationship('DomainEvent', backref='notification_records')
    user = db.relationship('User', backref='notification_records')
    user_query = db.relationship('UserQuery', backref='notification_records')
    item = db.relationship('Item', backref='notification_records')

class Keyword(db.Model):
    __tablename__ = 'keywords'
    keyword_id = db.Column(
        db.BigInteger,
        primary_key=True,
        server_default=text("nextval('keywords_keyword_id_seq'::regclass)")
    )
    keyword_text = db.Column(db.String(255), nullable=False)
    
class KeywordItems(db.Model):
    __tablename__ = 'keyword_items'
    keyword_id = db.Column(
        db.BigInteger,  # Changed from Integer
        db.ForeignKey('keywords.keyword_id'), 
        primary_key=True, 
        nullable=False
    )
    item_id = db.Column(
        db.BigInteger,  # Changed from Integer
        db.ForeignKey('items.item_id'), 
        primary_key=True, 
        nullable=False
    )
    found_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    item = db.relationship('Item', backref='keyword_associations')

# Feedback data to train the ML model
class ItemRelevanceFeedback(db.Model):
    id = db.Column(
        db.BigInteger,  # Changed from Integer
        primary_key=True,
        autoincrement=True,  # Explicitly enable auto-increment
        server_default=text("nextval('item_relevance_feedback_id_seq'::regclass)")
    )
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.BigInteger, db.ForeignKey('items.item_id'), nullable=False)
    keyword_id = db.Column(db.Integer, db.ForeignKey('keywords.keyword_id'), nullable=False)
    required_keywords = db.Column(db.String(255), nullable=True)
    excluded_keywords = db.Column(db.String(255), nullable=True)
    is_relevant = db.Column(db.Boolean, nullable=True)  # True/False for user feedback
    simple_hybrid_levenshtein_confidence = db.Column(db.Float)  # Optional: Hybrid confidence score
    cosine_similarity = db.Column(db.Float)  # Optional: Cosine similarity score
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_id', 'keyword_id', 
                          name='uq_user_item_keyword_feedback'),
    )

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feedback_type = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    email = db.Column(db.String(120))
    rating = db.Column(db.Integer)
    message = db.Column(db.Text)
    cancellation_reasons = db.Column(db.String(255))  # Comma-separated reasons
    cancellation_comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

#**********************
#HELPER FUNCTIONS
#**********************

def copy_item(source, target):
    """Copy fields between ItemBase subclasses, excluding id"""
    excluded_attrs = {'id', '_sa_instance_state'}
    for attr in vars(source).keys():
        if (
            not attr.startswith('_') 
            and attr not in excluded_attrs
            and hasattr(target, attr)
        ):
            setattr(target, attr, getattr(source, attr))