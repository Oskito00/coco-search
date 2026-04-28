"""Application configuration. JSON-API + RQ workers — no APScheduler / WTF."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from ebay_client.config import load_ebay_credentials

load_dotenv(override=True)


class Config:
    ENV = os.environ.get("APP_ENV", "production")
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    TESTING = False
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    SECRET_KEY = os.environ.get("SECRET_KEY")
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT")

    TIMEZONE = os.environ.get("TIMEZONE", "Europe/London")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.environ.get("DB_POOL_SIZE", 10)),
        "max_overflow": int(os.environ.get("DB_POOL_OVERFLOW", 20)),
        "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", 30)),
        "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", 1800)),
        "pool_pre_ping": True,
    }

    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    PUBLIC_APP_URL = os.environ.get("PUBLIC_APP_URL", "http://localhost:3000")

    # Mail
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 465))
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "1") == "1"
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "0") == "1"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = ("Coco", os.environ.get("MAIL_FROM", "cocosearchhelp@gmail.com"))

    # Stripe
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_INDIVIDUAL = os.environ.get("STRIPE_PRICE_INDIVIDUAL")
    STRIPE_PRICE_BUSINESS = os.environ.get("STRIPE_PRICE_BUSINESS")
    STRIPE_PRICE_PRO = os.environ.get("STRIPE_PRICE_PRO")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

    # eBay
    EBAY_ENV = os.environ.get("EBAY_ENV", "sandbox")
    EBAY_API_URL = os.environ.get("EBAY_API_URL")
    EBAY_CLIENT_ID = os.environ.get("EBAY_CLIENT_ID")
    EBAY_CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET")
    EBAY_ACCESS_TOKEN = os.environ.get("EBAY_ACCESS_TOKEN")
    EBAY_CREDENTIALS = load_ebay_credentials()

    IS_BETA = os.environ.get("IS_BETA", "0") == "1"

    @classmethod
    def verify(cls) -> None:
        required = {"ENCRYPTION_KEY": cls.ENCRYPTION_KEY, "SECRET_KEY": cls.SECRET_KEY}
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise RuntimeError(f"Missing required config values: {missing}")


class DevelopmentConfig(Config):
    ENV = "development"
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql:///ebay_checker"
    )


class TestingConfig(Config):
    ENV = "testing"
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL", "postgresql:///ebay_checker_test"
    )


def _normalize_db_url(url: str) -> str:
    if not url:
        return url
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


class ProductionConfig(Config):
    ENV = "production"
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.environ.get("DATABASE_URL", ""))


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
