"""
Redis-backed implementation of IJobStore.

Stores job metadata as JSON hashes in Redis DB 2 with TTL.
Maintains a sorted set for efficient list_recent() queries.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import redis

from src.domain.entities.job import Job
from src.domain.ports.job_store import IJobStore
from src.domain.value_objects.enums import JobPriority, JobStatus, JobType
from src.infrastructure.config import settings
from src.infrastructure.redis_client import get_job_store_redis

logger = logging.getLogger(__name__)

JOB_KEY_PREFIX = "job:"
RECENT_JOBS_KEY = "jobs:recent"


class RedisJobStore(IJobStore):
    """IJobStore implementation using Redis hashes and sorted sets."""

    def __init__(self, redis_client: redis.Redis | None = None):
        self._redis = redis_client

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = get_job_store_redis()
        return self._redis

    def save(self, job: Job) -> None:
        key = f"{JOB_KEY_PREFIX}{job.job_id}"
        data = self._serialize(job)
        try:
            self.redis.set(key, json.dumps(data), ex=settings.job_result_ttl)
            self.redis.zadd(
                RECENT_JOBS_KEY,
                {job.job_id: job.created_at.timestamp()},
            )
        except redis.RedisError as e:
            logger.error("Failed to save job %s: %s", job.job_id, e)
            raise

    def get(self, job_id: str) -> Optional[Job]:
        key = f"{JOB_KEY_PREFIX}{job_id}"
        try:
            raw = self.redis.get(key)
            if raw is None:
                return None
            return self._deserialize(json.loads(raw))
        except redis.RedisError as e:
            logger.error("Failed to get job %s: %s", job_id, e)
            return None

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        job = self.get(job_id)
        if job is None:
            logger.warning("Cannot update status: job %s not found", job_id)
            return

        job.status = status
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        if status in (JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.CANCELLED):
            job.completed_at = datetime.now(timezone.utc)

        self.save(job)

    def list_recent(self, limit: int = 20) -> list[Job]:
        try:
            job_ids = self.redis.zrevrange(RECENT_JOBS_KEY, 0, limit - 1)
            jobs = []
            for job_id in job_ids:
                job = self.get(job_id)
                if job is not None:
                    jobs.append(job)
            return jobs
        except redis.RedisError as e:
            logger.error("Failed to list recent jobs: %s", e)
            return []

    def delete(self, job_id: str) -> bool:
        key = f"{JOB_KEY_PREFIX}{job_id}"
        try:
            deleted = self.redis.delete(key)
            self.redis.zrem(RECENT_JOBS_KEY, job_id)
            return deleted > 0
        except redis.RedisError as e:
            logger.error("Failed to delete job %s: %s", job_id, e)
            return False

    @staticmethod
    def _serialize(job: Job) -> dict[str, Any]:
        return {
            "job_id": job.job_id,
            "job_type": job.job_type.value,
            "priority": job.priority.value,
            "status": job.status.value,
            "payload": job.payload,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
        }

    @staticmethod
    def _deserialize(data: dict[str, Any]) -> Job:
        return Job(
            job_id=data["job_id"],
            job_type=JobType(data["job_type"]),
            priority=JobPriority(data["priority"]),
            status=JobStatus(data["status"]),
            payload=data.get("payload", {}),
            result=data.get("result"),
            error=data.get("error"),
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )


redis_job_store = RedisJobStore()
