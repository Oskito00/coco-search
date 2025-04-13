import pytest
from app import create_app, db
from app.models import User, UserQuery, Keyword
from datetime import datetime, timedelta, timezone
from config import TestingConfig
import os

# Fixture: Create a Flask app for testing
@pytest.fixture(scope='session')
def app():
    """Session-wide test application"""
    app = create_app(TestingConfig)
    
    # Verify we're using the test database
    assert 'ebay_checker_test' in app.config['SQLALCHEMY_DATABASE_URI'], \
        "Not using test database!"
    
    # Push application context for the whole test session
    ctx = app.app_context()
    ctx.push()
    
    yield app
    
    # Remove context after tests
    ctx.pop()

@pytest.fixture(scope='session')
def _db(app):
    """Provide database access for all tests"""
    return db

# Fixture: HTTP test client
@pytest.fixture(scope='function')
def client(app):
    """Test client for making requests"""
    return app.test_client()

# Fixture: Database session
@pytest.fixture(scope='module')
def db_session(app):
    with app.app_context():
        yield db.session
        db.session.rollback()  # Undo uncommitted changes

# Fixture: Prepopulated test user
@pytest.fixture(scope='function')
def test_user(app):
    """Create and clean up test user"""
    with app.app_context():
        # Create test user
        user = User.query.filter_by(email="test_user@example.com").first()
        if not user:
            user = User(
                email="test_user@example.com",
                username="load_test_user",
                first_name="Load",
                last_name="Test"
            )
            user.set_password("testpass123")
            db.session.add(user)
            db.session.commit()
        
        yield user
        
        # Cleanup: Delete only test user's data
        UserQuery.query.filter_by(user_id=user.id).delete()
        Keyword.query.filter(Keyword.keyword_text.like('load-test-%')).delete()
        db.session.delete(user)
        db.session.commit()

@pytest.fixture(scope='module')
def runner(app):
    """CLI runner fixture"""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def clean_db(app):
    """Per-test cleanup of residual data"""
    with app.app_context():
        # Delete any remaining test queries
        UserQuery.query.filter(UserQuery.user.has(email="test_user@example.com")).delete()
        # Cleanup orphaned keywords
        Keyword.query.filter(Keyword.keyword_text.like('load-test-%')).delete()
        db.session.commit()
    yield

@pytest.fixture(scope='session', autouse=True)
def create_test_db(app):
    """Create test database tables once per session"""
    with app.app_context():
        db.create_all()
