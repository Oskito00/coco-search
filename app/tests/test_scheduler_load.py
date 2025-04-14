import time
import random
import uuid
import logging
import threading
import pytest
from datetime import datetime
from flask import current_app
from app import db
from app.models import UserQuery, Keyword, User
from app._scheduler.job_manager import add_query_jobs

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Test configuration
NUM_TEST_QUERIES = 100
STAGGER_SECONDS = 2  # 2 seconds between query creation
MONITORING_DURATION = 300  # 5 minutes

# Shared test statistics
test_stats = {
    'queries_created': 0,
    'jobs_created': 0,
    'api_calls_made': 0,
    'rate_limit_hits': 0,
    'start_time': None,
    'end_time': None,
    'lock': threading.Lock()
}

@pytest.fixture(scope='module')
def test_user(app):
    """Create a test user for all queries"""
    with app.app_context():
        user = User.query.filter_by(email="test_user@example.com").first()
        if not user:
            user = User(
                email="test_user@example.com",
            )
            user.set_password("testpass123")
            db.session.add(user)
            db.session.commit()
        yield user
        # Cleanup
        UserQuery.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()

def create_test_query(index, user_id):
    """Create a test query with associated keyword"""
    # Create keyword
    keyword = Keyword(
        keyword_text=f"load-test-{index}-{uuid.uuid4().hex[:6]}"

    )
    db.session.add(keyword)
    db.session.commit()

    # Create user query
    return UserQuery(
        user_id=user_id,
        keyword=keyword,
        min_price=random.randint(10, 50),
        max_price=random.randint(100, 500),
        is_active=True,
        check_interval=5  # Minutes
    )

@pytest.fixture(scope='module')
def setup_teardown(app):
    """Fixture to setup and teardown test data"""
    with app.app_context():
        # Cleanup any existing test queries
        Keyword.query.filter(Keyword.keyword_text.like('test-%')).delete()
        db.session.commit()
        yield
        # Teardown after test completes
        Keyword.query.filter(Keyword.keyword_text.like('test-%')).delete()
        db.session.commit()

def track_api_calls(monkeypatch):
    """Monkeypatch to track API calls and rate limits"""
    from app.utils.scraper import scrape_ebay  # Import your actual function

    def wrapper(*args, **kwargs):
        with test_stats['lock']:
            test_stats['api_calls_made'] += 1
        
        try:
            return scrape_ebay(*args, **kwargs)
        except Exception as e:
            if "rate limit" in str(e).lower():
                with test_stats['lock']:
                    test_stats['rate_limit_hits'] += 1
            raise

    monkeypatch.setattr('app.utils.scraper.scrape_ebay', wrapper)


@pytest.mark.load_test
def test_scheduler_with_100_queries(app, test_user):
    """Test creating 100 queries with staggered creation"""
    with app.app_context():
        # Calculate expected duration
        stagger_min = 0.5  # Minimum seconds between queries
        stagger_max = 3.0  # Maximum seconds between queries
        expected_duration = 100 * (stagger_min + stagger_max)/2
        logger.info(f"Expected setup duration: {expected_duration/60:.1f} minutes")
        
        start_time = time.time()
        
        # Create queries with random stagger
        for i in range(200):
            # Create and add query
            query = create_test_query(i, test_user.id)
            db.session.add(query)
            db.session.commit()
            add_query_jobs(query.query_id)
            
            # Log progress every 10 queries
            if (i+1) % 10 == 0:
                elapsed = time.time() - start_time
                logger.info(f"Created {i+1}/100 queries ({elapsed:.1f}s elapsed)")
            
            # Random stagger between queries (except after last one)
            if i < 99:
                delay = random.uniform(stagger_min, stagger_max)
                time.sleep(delay)
        
        # Final progress update
        total_duration = time.time() - start_time
        logger.info(f"Created all 100 queries in {total_duration/60:.1f} minutes")
        
        # Continue with monitoring phase...
        logger.info("Starting 5-minute monitoring period...")
        time.sleep(900)
