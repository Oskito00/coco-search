import os
from dotenv import load_dotenv
import logging
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy import create_engine

load_dotenv(override=True)  # Load .env file

project_root = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

    TIMEZONE = os.getenv('TIMEZONE', 'Europe/London')

    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    EBAY_ENV = os.getenv('EBAY_ENV', 'sandbox')
    EBAY_API_URL = os.getenv('EBAY_API_URL')
    EBAY_CLIENT_ID = os.getenv('EBAY_CLIENT_ID')
    EBAY_CLIENT_SECRET = os.getenv('EBAY_CLIENT_SECRET')
    EBAY_ACCESS_TOKEN = os.getenv('EBAY_ACCESS_TOKEN')

    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.getenv('CSRF_SECRET_KEY')
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = 'INFO'
    TESTING = False

    #Gmail authentication
    SECURITY_PASSWORD_SALT = os.getenv('SECURITY_PASSWORD_SALT')

    @classmethod
    def verify(cls):
        required = {
            'EBAY_CLIENT_ID': cls.EBAY_CLIENT_ID,
            'EBAY_CLIENT_SECRET': cls.EBAY_CLIENT_SECRET,
            'ENCRYPTION_KEY': cls.ENCRYPTION_KEY
        }
        
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise RuntimeError(f"Missing required config values: {missing}")

        if cls.DEBUG and cls.FLASK_ENV == 'production':
            raise ValueError("DEBUG mode should never be enabled in production")

    @classmethod
    def get(cls, key, default=None):
        return getattr(cls, key, default)

class TestingConfig(Config):
    EBAY_CLIENT_ID = os.getenv('EBAY_CLIENT_ID')
    EBAY_CLIENT_SECRET = os.getenv('EBAY_CLIENT_SECRET')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    TESTING = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TELEGRAM_BOT_TOKEN = '7914809074'

class DevelopmentConfig(Config):
    FLASK_ENV = 'development'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(project_root, "instance/app.db")}'

    # Scheduler
    SCHEDULER_JOBSTORES = {
        'default': {
            'type': 'sqlalchemy',
            'url': SQLALCHEMY_DATABASE_URI  # Use your existing database URI
        }
    }
    SCHEDULER_EXECUTORS = {'default': {'type': 'threadpool', 'max_workers': 20}}
    SCHEDULER_COALESCE = True

    #Mail configs
    MAIL_DEFAULT_SENDER = ('NOREPLY', 'noreply@ebaymonitor.com')
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

    #Stripe
    STRIPE_PRICE_INDIVIDUAL = os.getenv('STRIPE_PRICE_INDIVIDUAL')
    STRIPE_PRICE_BUSINESS = os.getenv('STRIPE_PRICE_BUSINESS')
    STRIPE_PRICE_PRO = os.getenv('STRIPE_PRICE_PRO')
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

    SQLALCHEMY_ECHO = False
    DEBUG = False
    # Read IS_BETA from environment variable, default to False
    IS_BETA = os.getenv('IS_BETA', '').lower() in ('true', 'yes', '1')

class ProductionConfig(Config):
    FLASK_ENV = 'production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace(
        'postgres://', 'postgresql://', 1
    )

    # Mail configs - remove commas at end of lines
    MAIL_SERVER = 'smtp.mailgun.org'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'postmaster@sandbox97899069c87a42bc8be143e9f92ee3a7.mailgun.org'
    MAIL_PASSWORD = 'd4e78637428d4b2317873133804d0f9c-3d4b3a2a-1002e7c3'
    MAIL_DEFAULT_SENDER = 'postmaster@sandbox97899069c87a42bc8be143e9f92ee3a7.mailgun.org'

    DEBUG = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'echo_pool': False,
        'hide_parameters': True
    }

    SCHEDULER_RUN = os.environ.get('DYNO') in ('web.1', None)
    SCHEDULER_API_ENABLED = False

    IS_BETA = os.getenv('IS_BETA', '').lower() in ('true', 'yes', '1')

    # Force HTTPS
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'
    
    # HTTP Strict Transport Security
    SECURITY_HSTS_ENABLED = True
    SECURITY_HSTS_SECONDS = 31536000  # 1 year
    SECURITY_HSTS_INCLUDE_SUBDOMAINS = True
    SECURITY_HSTS_PRELOAD = True

    

    def __init__(self):
        self.validate_mail_config()
    
    def validate_mail_config(self):
        """Explicit mail configuration validation"""
        if not isinstance(self.MAIL_SERVER, str):
            raise TypeError(f"MAIL_SERVER must be string, got {type(self.MAIL_SERVER)}")
        if not isinstance(self.MAIL_PORT, int):
            raise TypeError(f"MAIL_PORT must be integer, got {type(self.MAIL_PORT)}")


class SchedulerConfig:
    JOBSTORE_URI = os.getenv('SCHEDULER_DATABASE_URI')
    JOBSTORE_TABLE = 'apscheduler_jobs'
    TIMEZONE = os.getenv('TIMEZONE')


config = {
    'development':  DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
} 