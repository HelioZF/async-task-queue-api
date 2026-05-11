"""FastAPI router for health checks and queue statistics."""

import logging

import redis
from fastapi import APIRouter

from src.application.dtos.job_dtos import HealthResponse, QueueStatsResponse
from src.infrastructure.celery_app import celery_app
from src.infrastructure.config import settings
from src.infrastructure.rate_limiter import rate_limiter

router = APIRouter(tags=["Monitoring"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check for all system components."""
    components: dict[str, str] = {
        "redis": "unknown",
        "workers": "unknown",
        "queues": "unknown",
    }

    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        components["redis"] = "healthy"
    except Exception as e:
        components["redis"] = f"unhealthy: {e}"

    # Check workers
    try:
        inspect = celery_app.control.inspect(timeout=2.0)
        stats = inspect.stats()
        if stats:
            components["workers"] = f"healthy ({len(stats)} workers active)"
        else:
            components["workers"] = "unhealthy (no workers active)"
    except Exception as e:
        components["workers"] = f"unhealthy: {e}"

    # Check queues
    try:
        inspect = celery_app.control.inspect(timeout=2.0)
        active = inspect.active()
        if active is not None:
            components["queues"] = "healthy"
        else:
            components["queues"] = "unhealthy (cannot inspect queues)"
    except Exception as e:
        components["queues"] = f"unhealthy: {e}"

    is_healthy = all("healthy" in str(s).lower() for s in components.values())

    return HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        components=components,
    )


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def queue_stats() -> QueueStatsResponse:
    """Detailed queue statistics and rate limit status."""
    try:
        inspect = celery_app.control.inspect(timeout=2.0)
        stats = inspect.stats()
        active = inspect.active()
        scheduled = inspect.scheduled()
        reserved = inspect.reserved()

        # Queue depths via Redis llen
        queue_depths: dict[str, int] = {}
        try:
            r = redis.from_url(settings.redis_url)
            for q_name in [settings.queue_jobs_high, settings.queue_jobs_low]:
                queue_depths[q_name] = r.llen(q_name)
        except Exception as e:
            logger.error("Error reading queue depths: %s", e)

        # Rate limit stats
        rate_stats = {
            "file_processing": {
                "current_count": rate_limiter.get_current_count("file_processing"),
                "limit": settings.rate_limit_max_requests,
                "window": f"{settings.rate_limit_window}s",
                "available": max(
                    0,
                    settings.rate_limit_max_requests
                    - rate_limiter.get_current_count("file_processing"),
                ),
            }
        }

        return QueueStatsResponse(
            workers={
                "total": len(stats) if stats else 0,
                "stats": stats or {},
            },
            tasks={
                "active": sum(len(t) for t in (active or {}).values()),
                "scheduled": sum(len(t) for t in (scheduled or {}).values()),
                "reserved": sum(len(t) for t in (reserved or {}).values()),
            },
            queue_depths=queue_depths,
            rate_limiting=rate_stats,
        )

    except Exception as e:
        logger.error("Error getting queue stats: %s", e)
        return QueueStatsResponse(
            workers={"error": str(e)},
            tasks={},
            queue_depths={},
            rate_limiting={},
        )
