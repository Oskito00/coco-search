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
    
    #Stripe
    STRIPE_PRICE_INDIVIDUAL = os.getenv('STRIPE_PRICE_INDIVIDUAL')
    STRIPE_PRICE_BUSINESS = os.getenv('STRIPE_PRICE_BUSINESS')
    STRIPE_PRICE_PRO = os.getenv('STRIPE_PRICE_PRO')
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

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

    SQLALCHEMY_ECHO = False
    DEBUG = False

class ProductionConfig(Config):
    FLASK_ENV = 'production'
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')

    #Mail configs
    MAIL_DEFAULT_SENDER = ('MAIL_FROM', 'noreply@ebaymonitor.com')

    DEBUG = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'echo_pool': False,
        'hide_parameters': True
    }

class SchedulerConfig:
    JOBSTORE_URI = os.getenv('SCHEDULER_DATABASE_URI')
    JOBSTORE_TABLE = 'apscheduler_jobs'
    TIMEZONE = os.getenv('TIMEZONE')


config = {
    'development':  DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
} 