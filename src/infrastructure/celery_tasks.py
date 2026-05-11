"""
Celery task definitions.

Single generic task that dispatches to the appropriate file processor
based on job_type. Handles status updates, retries, and rate limiting.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from celery import Task

from src.infrastructure.celery_app import celery_app
from src.infrastructure.rate_limiter import rate_limiter
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)


class RateLimitedTask(Task):
    """Base task class with rate limiting hook."""

    pass


@celery_app.task(
    bind=True,
    base=RateLimitedTask,
    name="src.infrastructure.celery_tasks.process_job",
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def process_job(
    self,
    job_id: str,
    job_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Process a file processing job.

    This is the single Celery task for all job types. It dispatches
    to the appropriate processor based on job_type.

    Args:
        job_id: UUID of the job.
        job_type: One of: csv_summary, word_count, image_resize, pdf_extract.
        payload: Dict with file_content (base64) and filename.

    Returns:
        Dict with processing result on success.

    Raises:
        self.retry: On rate limit or transient errors.
        Exception: On permanent failure (serialized as JSON).
    """
    logger.info("Processing job %s (type: %s)", job_id, job_type)

    # Import here to avoid circular imports at module level
    from src.adapters.outbound.processors import PROCESSOR_REGISTRY
    from src.adapters.outbound.redis_job_store import redis_job_store
    from src.domain.value_objects.enums import JobStatus, JobType

    try:
        # Check rate limit
        if not rate_limiter.is_allowed("file_processing"):
            logger.warning("Rate limit exceeded, retrying job %s", job_id)
            raise self.retry(countdown=5, max_retries=10)

        # Update status to processing
        redis_job_store.update_status(job_id, JobStatus.PROCESSING)

        # Dispatch to processor
        job_type_enum = JobType(job_type)
        processor = PROCESSOR_REGISTRY.get(job_type_enum)

        if processor is None:
            raise ValueError(f"No processor registered for job type: {job_type}")

        # Execute processing
        result = processor.process(payload)

        # Update status to success
        redis_job_store.update_status(job_id, JobStatus.SUCCESS, result=result)

        logger.info("Job %s completed successfully", job_id)
        return {"success": True, "job_id": job_id, "result": result}

    except self.MaxRetriesExceededError:
        error_msg = f"Job {job_id} exceeded maximum retries"
        logger.error(error_msg)
        redis_job_store.update_status(job_id, JobStatus.FAILED, error=error_msg)
        raise

    except Exception as e:
        error_detail = {
            "error_type": type(e).__name__,
            "message": str(e),
            "job_id": job_id,
            "job_type": job_type,
        }
        logger.error("Job %s failed: %s", job_id, error_detail)

        # Update store with failure
        try:
            from src.adapters.outbound.redis_job_store import redis_job_store
            from src.domain.value_objects.enums import JobStatus

            redis_job_store.update_status(
                job_id, JobStatus.FAILED, error=str(e)
            )
        except Exception:
            logger.exception("Failed to update job store for %s", job_id)

        raise Exception(json.dumps(error_detail))
