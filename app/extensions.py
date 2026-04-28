"""Flask extension singletons. JSON-API only — no Login/CSRF/Talisman/Scheduler."""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.utils.security import DataEncryptor

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
encryptor = DataEncryptor()
limiter = Limiter(storage_uri="memory://", key_func=get_remote_address)
