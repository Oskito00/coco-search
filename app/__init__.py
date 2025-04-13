from dotenv import load_dotenv
from flask import Flask, redirect, request
from app.extensions import (db, init_scheduler_tables, migrate, login_manager, csrf, encryptor, mail, limiter, scheduler)
from flask_wtf.csrf import CSRFProtect
from app.jobs.snyc_jobs import sync_jobs
from app.utils.print_helpers import print_scheduler_settings
from .forms import csrf
import os
from config import DevelopmentConfig, ProductionConfig, TestingConfig, config as app_config
from flask_talisman import Talisman
from datetime import datetime
from tzlocal import get_localzone



csrf = CSRFProtect()

talisman = Talisman(
    content_security_policy={
        'default-src': "'self'",
        'script-src': [
            "'self'",
            'https://cdn.jsdelivr.net',
            "'unsafe-inline'"  # Only if absolutely necessary
        ],
        'style-src': [
            "'self'",
            'https://fonts.googleapis.com',
            "'unsafe-inline'"
        ]
    },
    force_https=False,  # Disable for all environments
    session_cookie_secure=False,
    hsts=False  # Completely disable HSTS
)

def create_app(env_name=None):
    load_dotenv(override=True)
    app = Flask(__name__)

    print("ENV: ", os.environ.get('APP_ENV'))

    is_test = os.environ.get('APP_ENV') == 'testing'
    is_development = os.environ.get('APP_ENV') == 'development'
    is_production = os.environ.get('APP_ENV') == 'production'

    # Auto-detect environment first
    if os.environ.get('DYNO'):
        cfg = ProductionConfig
        app.logger.info("🚀 Heroku production environment detected")
        @app.before_request
        def enforce_https():
            if not request.is_secure:
                url = request.url.replace('http://', 'https://', 1)
                code = 301
                return redirect(url, code=code)
    elif is_test:
        cfg = TestingConfig
        app.logger.info("🧪 Testing environment detected")
    else:
        cfg = DevelopmentConfig
        app.logger.info("💻 Local development environment detected")
    
    # Load configuration
    app.config.from_object(cfg)
    
    # Verify configuration after loading
    try:
        cfg.verify()  # Should be called on the CLASS, not instance
        app.logger.info("✅ Configuration verified successfully")
    except ValueError as e:
        app.logger.error("❌ Configuration verification failed: %s", e)
        raise
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    encryptor.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)


    # Initialize scheduler AFTER database with explicit timezone
    scheduler.init_app(app)
    
    # Set scheduler timezone to system local timezone (handles DST automatically)
    local_tz = get_localzone()
    scheduler.timezone = local_tz
    print(f"Initialized scheduler with timezone: {local_tz}")
    print(f"Current time in this timezone: {datetime.now(local_tz)}")
    
    # Start the scheduler AFTER setting timezone
    scheduler.start()

    print_scheduler_settings(app, scheduler)
    
    # Add jobs in context
    with app.app_context():
        scheduler.add_job(
            id='sync_jobs',           # Unique job ID
            func=sync_jobs,           # Function to execute
            trigger='interval',       # Trigger type
            minutes=1,                # This is a trigger argument
            timezone=local_tz,        # Use the same timezone
            replace_existing=True     # Replace if job exists
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
    print(f"Active config: {os.environ.get('APP_ENV')}")
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Only enable security headers in production
    if is_production == True:
        talisman.init_app(app)
    else:
        print("Debug mode is enabled. Security headers are disabled.")
        talisman.init_app(
            app,
            force_https=False,
            session_cookie_secure=False,
            content_security_policy=None
        )

    print("IS BETA: ", app.config['IS_BETA'])
    
    return app
