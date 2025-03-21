from dotenv import load_dotenv
from flask import Flask
from app.extensions import (db, migrate, login_manager, csrf, encryptor, mail, limiter, scheduler)
from flask_wtf.csrf import CSRFProtect
from app.jobs.snyc_jobs import sync_jobs
from .forms import csrf
import os
from config import config as app_config



csrf = CSRFProtect()

def create_app(env_name=None):
    load_dotenv(override=True)
    app = Flask(__name__)

    # Determine environment
    env = os.getenv('FLASK_ENV', 'development').lower()
    
    try:
        # 2. Load the appropriate config class
        cfg = app_config[env]
        app.config.from_object(cfg)
        
        # 3. Verify configuration
        cfg.verify()  # Call verify() on the config CLASS
        
    except KeyError:
        raise ValueError(f"Invalid FLASK_ENV: {env}. Valid options: {list(app_config.keys())}")
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    encryptor.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # Initialize scheduler AFTER database
    scheduler.init_app(app)
    
    # Start scheduler AFTER all extensions
    scheduler.start()
    
    # Add jobs in context
    with app.app_context():
        scheduler.add_job(
        id='sync_jobs',              # Unique job ID
        func=sync_jobs,             # Function to execute
        trigger='interval',         # Trigger type
        seconds=10,                 # This is a trigger argument
        replace_existing=True       # Replace if job exists
    )

    # Register blueprints
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.routes.queries import bp as queries_bp
    app.register_blueprint(queries_bp)

    from app.routes.subscription import bp as subscription_bp
    app.register_blueprint(subscription_bp)

    from app.stripe.webhooks import webhook_bp
    app.register_blueprint(webhook_bp, url_prefix='/stripe')
    csrf.exempt(webhook_bp)

    from app.routes.telegram import bp as telegram_bp
    app.register_blueprint(telegram_bp, url_prefix='/telegram')

    from app.routes.settings import bp as settings_bp
    app.register_blueprint(settings_bp, url_prefix='/settings')

    from app.routes.contact_feedback import bp as contact_feedback_bp
    app.register_blueprint(contact_feedback_bp, url_prefix='/contact_feedback')

    # Debug output
    print(f"Active config: {env_name}")
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
    return app
