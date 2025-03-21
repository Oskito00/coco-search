from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from app.utils.security import DataEncryptor
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_apscheduler import APScheduler


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
csrf = CSRFProtect()
encryptor = DataEncryptor()
mail = Mail()
scheduler = APScheduler()
limiter = Limiter(
    storage_uri="memory://",  # Explicit in-memory
    key_func=get_remote_address
)

# User loader must be after model definition
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

login_manager.user_loader(load_user) 


