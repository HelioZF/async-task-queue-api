"""
Redis connection factory.

Provides lazy singleton connections for the job store (DB 2).
Broker (DB 0) and result backend (DB 1) are managed by Celery.
"""

import redis

from src.infrastructure.config import settings

_job_store_client: redis.Redis | None = None


def get_job_store_redis() -> redis.Redis:
    """Get or create the Redis client for the job metadata store (DB 2)."""
    global _job_store_client
    if _job_store_client is None:
        _job_store_client = redis.from_url(
            settings.redis_job_store_url,
            decode_responses=True,
        )
    return _job_store_client
