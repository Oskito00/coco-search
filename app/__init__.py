from dotenv import load_dotenv
from flask import Flask
from app.extensions import (db, migrate, login_manager, csrf, encryptor, mail, limiter, scheduler)
from flask_wtf.csrf import CSRFProtect
from app.jobs.snyc_jobs import sync_jobs
from .forms import csrf
import os
from config import DevelopmentConfig, ProductionConfig, config as app_config



csrf = CSRFProtect()

def create_app(env_name=None):
    load_dotenv(override=True)
    app = Flask(__name__)

    # Auto-detect environment first
    if os.environ.get('DYNO'):
        cfg = ProductionConfig
        app.logger.info("🚀 Heroku production environment detected")
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
