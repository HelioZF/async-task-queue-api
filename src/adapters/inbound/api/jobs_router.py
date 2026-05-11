"""FastAPI router for job submission, status polling, cancellation, and listing."""

from fastapi import APIRouter, Query

from src.adapters.outbound.redis_job_store import redis_job_store
from src.application.dtos.job_dtos import (
    JobListResponse,
    JobStatusResponse,
    JobSubmitRequest,
    JobSubmitResponse,
)
from src.application.mappers.job_mapper import JobMapper
from src.application.use_cases.cancel_job import CancelJobUseCase
from src.application.use_cases.get_job_status import GetJobStatusUseCase
from src.application.use_cases.list_jobs import ListJobsUseCase
from src.application.use_cases.submit_job import SubmitJobUseCase

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _get_submit_use_case() -> SubmitJobUseCase:
    return SubmitJobUseCase(job_store=redis_job_store)


def _get_status_use_case() -> GetJobStatusUseCase:
    return GetJobStatusUseCase(job_store=redis_job_store)


def _get_cancel_use_case() -> CancelJobUseCase:
    return CancelJobUseCase(job_store=redis_job_store)


def _get_list_use_case() -> ListJobsUseCase:
    return ListJobsUseCase(job_store=redis_job_store)


@router.post("", response_model=JobSubmitResponse, status_code=202)
async def submit_job(request: JobSubmitRequest) -> JobSubmitResponse:
    """Submit a new file processing job to the queue."""
    use_case = _get_submit_use_case()
    job = use_case.execute(
        job_type=request.job_type,
        payload=request.payload,
        priority=request.priority,
    )
    return JobMapper.to_submit_response(job)


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get the current status of a job."""
    use_case = _get_status_use_case()
    job = use_case.execute(job_id)
    return JobMapper.to_status_response(job)


@router.delete("/{job_id}")
async def cancel_job(job_id: str) -> dict:
    """Cancel a pending or processing job."""
    use_case = _get_cancel_use_case()
    job = use_case.execute(job_id)
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "message": (
            "Job cancelled successfully."
            if job.status.value == "cancelled"
            else f"Job cannot be cancelled (already in terminal state)."
        ),
        "previous_status": job.status.value,
    }


@router.get("", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100, description="Max jobs to return"),
) -> JobListResponse:
    """List recent jobs."""
    use_case = _get_list_use_case()
    jobs = use_case.execute(limit=limit)
    return JobMapper.to_list_response(jobs)
