"""
Application configuration using Pydantic Settings.

All settings are overridable via environment variables
with the TASKQUEUE_ prefix. Load from .env file if present.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application and queue configuration."""

    # Application
    app_name: str = "Async Task Queue API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_result_backend: str = "redis://localhost:6379/1"
    redis_job_store_url: str = "redis://localhost:6379/2"

    # Celery
    celery_task_result_expires: int = 3600  # 1 hour
    celery_task_soft_time_limit: int = 300  # 5 minutes
    celery_task_time_limit: int = 360  # 6 minutes

    # Queues
    queue_jobs_high: str = "jobs_high"
    queue_jobs_low: str = "jobs_low"

    # Rate limiting
    rate_limit_max_requests: int = 60  # per minute
    rate_limit_window: int = 60  # seconds

    # Job store
    job_result_ttl: int = 3600  # 1 hour

    # Worker
    worker_prefetch_multiplier: int = 1
    worker_max_tasks_per_child: int = 100

    model_config = {
        "env_prefix": "TASKQUEUE_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
