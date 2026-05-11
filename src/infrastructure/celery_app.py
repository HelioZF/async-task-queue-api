"""
Celery application configuration.

Defines the broker, result backend, queue routing,
and global task settings. Workers are started separately
via shell scripts or docker-compose commands.
"""

from celery import Celery

from src.infrastructure.config import settings

celery_app = Celery(
    "file_processing_api",
    broker=settings.redis_url,
    backend=settings.redis_result_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task tracking
    task_track_started=True,
    task_acks_late=True,
    # Worker settings
    worker_prefetch_multiplier=settings.worker_prefetch_multiplier,
    worker_max_tasks_per_child=settings.worker_max_tasks_per_child,
    # Result backend
    result_expires=settings.celery_task_result_expires,
    # Task routing
    task_routes={
        "src.infrastructure.celery_tasks.process_job": {
            "queue": settings.queue_jobs_low,
        },
    },
    # Timeout settings
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    task_time_limit=settings.celery_task_time_limit,
)

celery_app.autodiscover_tasks(["src.infrastructure"])
