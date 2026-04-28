"""Lazy, process-singleton Redis connection used by all queue producers/consumers."""

from __future__ import annotations

import os

from redis import Redis

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(_redis_url(), decode_responses=False)
    return _redis


def _redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")
