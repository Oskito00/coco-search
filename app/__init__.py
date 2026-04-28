"""Flask app factory. JSON-only API; background work runs in separate processes."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from flask import Flask

from app.extensions import db, encryptor, limiter, mail, migrate
from config import DevelopmentConfig, ProductionConfig, TestingConfig


def create_app(config_class=None) -> Flask:
    load_dotenv(override=True)
    app = Flask(__name__)

    cfg = config_class or _select_config()
    app.config.from_object(cfg)
    cfg.verify()

    _init_extensions(app)
    _register_api(app)
    _configure_logging(app)

    return app


def _select_config():
    env = os.environ.get("APP_ENV", "production").lower()
    if env == "testing":
        return TestingConfig
    if env == "development":
        return DevelopmentConfig
    return ProductionConfig


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    encryptor.init_app(app)
    limiter.init_app(app)


def _register_api(app: Flask) -> None:
    from app.api import register_api  # local import to avoid circular import on models
    register_api(app)


def _configure_logging(app: Flask) -> None:
    level = app.config.get("LOG_LEVEL", "INFO")
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
