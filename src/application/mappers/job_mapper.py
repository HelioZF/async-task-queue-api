"""Mapper: converts Job entities to/from DTOs."""

from src.application.dtos.job_dtos import (
    JobListResponse,
    JobStatusResponse,
    JobSubmitResponse,
)
from src.domain.entities.job import Job
from src.domain.value_objects.enums import JobPriority


class JobMapper:
    """Converts between Job domain entities and application DTOs."""

    @staticmethod
    def to_submit_response(job: Job) -> JobSubmitResponse:
        estimated = "5-15 seconds" if job.priority == JobPriority.HIGH else "15-60 seconds"
        return JobSubmitResponse(
            job_id=job.job_id,
            status=job.status,
            priority=job.priority,
            message="Job submitted successfully.",
            check_status_url=f"/jobs/{job.job_id}",
            estimated_time=estimated,
        )

    @staticmethod
    def to_status_response(job: Job) -> JobStatusResponse:
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            job_type=job.job_type,
            result=job.result,
            error=job.error,
            created_at=job.created_at,
            completed_at=job.completed_at,
            retry_count=job.retry_count,
        )

    @staticmethod
    def to_list_response(jobs: list[Job]) -> JobListResponse:
        return JobListResponse(
            jobs=[JobMapper.to_status_response(j) for j in jobs],
            total=len(jobs),
        )
