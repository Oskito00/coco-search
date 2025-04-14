import os
from dotenv import load_dotenv
import logging
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy import create_engine

load_dotenv(override=True)  # Load .env file

project_root = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Load from environment first
    ENV = os.environ.get('APP_ENV', 'production')
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
    
    SECRET_KEY = os.getenv('SECRET_KEY')

    TIMEZONE = os.getenv('TIMEZONE', 'Europe/London')

    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    EBAY_ENV = os.getenv('EBAY_ENV', 'sandbox')
    EBAY_API_URL = os.getenv('EBAY_API_URL')
    EBAY_CLIENT_ID = os.getenv('EBAY_CLIENT_ID')
    EBAY_CLIENT_SECRET = os.getenv('EBAY_CLIENT_SECRET')
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

    EBAY_ACCESS_TOKEN = os.getenv('EBAY_ACCESS_TOKEN')

    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.getenv('CSRF_SECRET_KEY')
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = 'INFO'
    TESTING = False

    EBAY_CREDENTIALS = [
    {
        'client_id': 'OscarAlb-Monitor-PRD-5ded7de14-d6ea23c9',
        'client_secret': 'PRD-ded7de147834-332f-4231-8b70-afea',
        'token': None,          # Will be populated automatically
        'token_expiry': None   # Will be populated automatically
    },
    {
        'client_id': 'RoryAlbe-Itemsear-PRD-f4c82e554-b68b4152',
        'client_secret': 'PRD-4c82e5542278-55d5-44a7-a98e-8ca8',
        'token': None,
        'token_expiry': None
    },
    {
        'client_id': 'Cristian-Analysis-PRD-924562b2f-44eeb76f',
        'client_secret': 'PRD-24562b2f709c-4954-4de8-9832-4155',
        'token': None,
        'token_expiry': None
    },
    {
        'client_id': 'LesleyAl-esp32-PRD-10e8fd9f1-89a477f8',
        'client_secret': 'PRD-0e8fd9f1ff85-1b15-47f2-bf87-f652',
        'token': None,
        'token_expiry': None
    }
]
    
    #Gmail authentication
    SECURITY_PASSWORD_SALT = os.getenv('SECURITY_PASSWORD_SALT')

    @classmethod
    def verify(cls):
        required = {
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
    ENV = 'testing'
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "postgresql:///ebay_checker_test" 

    # Scheduler
    SCHEDULER_JOBSTORES = {
        'default': {
            'type': 'sqlalchemy',
            'url': SQLALCHEMY_DATABASE_URI  # Use your existing database URI
        }
    }
    SCHEDULER_EXECUTORS = {'default': {'type': 'threadpool', 'max_workers': 50}}
    SCHEDULER_COALESCE = True
    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': False,           # Process all missed job runs
        'max_instances': 10,         # Allow multiple instances of the same job
        'misfire_grace_time': 3600   # 1 hour grace time for missed jobs
    }

    # Improved database connection pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,             # Increase from current 10
        'max_overflow': 30,          # Increase from current 20
        'pool_timeout': 30,          # Increase from current 10
        'pool_recycle': 1800,        # 30 minutes instead of 5 minutes
        'pool_pre_ping': True        # Keep this setting
    }

    #Mail configs
    MAIL_DEFAULT_SENDER = ('Coco', 'noreply@coco.com')
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
    FORCE_HTTPS = False

    # Read IS_BETA from the environment variable
    IS_BETA = False

class DevelopmentConfig(Config):
    ENV = 'development'
    DEBUG = True
    FLASK_ENV = 'development'
    SQLALCHEMY_DATABASE_URI = "postgresql:///ebay_checker" 

    # Scheduler
    SCHEDULER_JOBSTORES = {
        'default': {
            'type': 'sqlalchemy',
            'url': SQLALCHEMY_DATABASE_URI  # Use your existing database URI
        }
    }
    SCHEDULER_EXECUTORS = {'default': {'type': 'threadpool', 'max_workers': 50}}
    SCHEDULER_COALESCE = True
    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': False,           # Process all missed job runs
        'max_instances': 10,         # Allow multiple instances of the same job
        'misfire_grace_time': 3600   # 1 hour grace time for missed jobs
    }

    # Improved database connection pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,             # Increase from current 10
        'max_overflow': 30,          # Increase from current 20
        'pool_timeout': 30,          # Increase from current 10
        'pool_recycle': 1800,        # 30 minutes instead of 5 minutes
        'pool_pre_ping': True        # Keep this setting
    }

    #Mail configs
    MAIL_DEFAULT_SENDER = ('Coco', 'noreply@coco.com')
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
    FORCE_HTTPS = False

    # Read IS_BETA from the environment variable
    IS_BETA = True

class ProductionConfig(Config):
    ENV = 'production'
    DEBUG = False
    FLASK_ENV = 'production'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace(
        'postgres://', 'postgresql://', 1
    ) + '?sslmode=require'

    # Scheduler
    SCHEDULER_JOBSTORES = {
        'default': {
            'type': 'sqlalchemy',
            'url': SQLALCHEMY_DATABASE_URI  # Use your existing database URI
        }
    }

    SCHEDULER_EXECUTORS = {'default': {'type': 'threadpool', 'max_workers': 50}}
    SCHEDULER_COALESCE = True
    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': False,           # Process all missed job runs
        'max_instances': 10,         # Allow multiple instances of the same job
        'misfire_grace_time': 3600   # 1 hour grace time for missed jobs
    }

    # Improved database connection pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,             # Increase from current 10
        'max_overflow': 30,          # Increase from current 20
        'pool_timeout': 30,          # Increase from current 10
        'pool_recycle': 1800,        # 30 minutes instead of 5 minutes
        'pool_pre_ping': True        # Keep this setting
    }

    # Mail configs - remove commas at end of lines
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'oscar.alberigo@gmail.com'
    MAIL_PASSWORD = 'ufvx hcav zmad gsct'
    MAIL_DEFAULT_SENDER = 'oscar.alberigo@gmail.com'

    DEBUG = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'echo_pool': False,
        'hide_parameters': True
    }

    SCHEDULER_RUN = os.environ.get('DYNO') in ('web.1', None)
    SCHEDULER_API_ENABLED = False

    IS_BETA = True

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