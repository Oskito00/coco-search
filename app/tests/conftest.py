import pytest
from app import create_app
from config import DevelopmentConfig


@pytest.fixture(scope='session')
def app():
    """Session-wide test application."""
    app = create_app(DevelopmentConfig)
    ctx = app.app_context()
    ctx.push()
    yield app
    ctx.pop()
