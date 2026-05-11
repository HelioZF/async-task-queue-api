"""
Redis-based sliding window rate limiter.

Uses sorted sets for atomic counting within a time window.
Critically implements FAIL-OPEN design: if Redis is unavailable,
requests are allowed through rather than blocked.

Adapted from legacy pattern (see docs/analysis/legacy-patterns.md #2).
"""

import logging
from time import time

import redis

from src.infrastructure.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding window rate limiter backed by Redis sorted sets."""

    def __init__(
        self,
        redis_url: str | None = None,
        key_prefix: str = "rate_limit",
    ):
        redis_url = redis_url or settings.redis_url
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.prefix = key_prefix

    def is_allowed(
        self,
        resource: str,
        max_requests: int | None = None,
        window: int | None = None,
    ) -> bool:
        """Check if a request is within the rate limit.

        Args:
            resource: Resource identifier (e.g. "file_processing").
            max_requests: Max requests per window. Defaults to config value.
            window: Window size in seconds. Defaults to config value.

        Returns:
            True if allowed, False if limit exceeded.
            Returns True (fail-open) if Redis is unavailable.
        """
        max_requests = max_requests or settings.rate_limit_max_requests
        window = window or settings.rate_limit_window
        key = f"{self.prefix}:{resource}"
        current_time = int(time())

        try:
            pipe = self.redis.pipeline()
            pipe.zadd(key, {str(current_time): current_time})
            pipe.zremrangebyscore(key, 0, current_time - window)
            pipe.zcard(key)
            pipe.expire(key, window + 10)
            results = pipe.execute()
            request_count = results[2]

            is_allowed = request_count <= max_requests

            if not is_allowed:
                logger.warning(
                    "Rate limit exceeded for %s: %d/%d in %ds",
                    resource,
                    request_count,
                    max_requests,
                    window,
                )

            return is_allowed

        except redis.RedisError as e:
            logger.error("Redis error in rate limiter: %s", e)
            return True  # Fail-open

    def get_current_count(self, resource: str, window: int | None = None) -> int:
        """Get the current request count within the window."""
        window = window or settings.rate_limit_window
        key = f"{self.prefix}:{resource}"
        current_time = int(time())

        try:
            self.redis.zremrangebyscore(key, 0, current_time - window)
            return self.redis.zcard(key)
        except redis.RedisError as e:
            logger.error("Redis error getting count: %s", e)
            return 0

    def reset(self, resource: str) -> None:
        """Reset the rate limit counter for a resource."""
        key = f"{self.prefix}:{resource}"
        try:
            self.redis.delete(key)
            logger.info("Rate limit reset for %s", resource)
        except redis.RedisError as e:
            logger.error("Redis error resetting rate limit: %s", e)


rate_limiter = RateLimiter()
