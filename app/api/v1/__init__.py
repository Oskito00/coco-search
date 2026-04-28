"""All v1 blueprints. Add a new module here to expose its routes."""

from app.api.v1.auth_routes import bp as auth_bp
from app.api.v1.health import bp as health_bp
from app.api.v1.items import bp as items_bp
from app.api.v1.notifications import bp as notifications_bp
from app.api.v1.searches import bp as searches_bp
from app.api.v1.subscription import bp as subscription_bp
from app.api.v1.users import bp as users_bp
from app.api.v1.webhooks import bp as webhooks_bp

V1_PREFIX = "/api/v1"

V1_BLUEPRINTS = [
    health_bp,
    auth_bp,
    users_bp,
    searches_bp,
    items_bp,
    notifications_bp,
    subscription_bp,
    webhooks_bp,
]
