"""
Application DTOs: Pydantic v2 models for API request/response contracts.

DTOs live in the application layer because they define the data shapes
exchanged between the inbound adapters (API routes) and use cases.
They are NOT domain entities.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.domain.value_objects.enums import JobPriority, JobStatus, JobType


# ── Request DTOs ──────────────────────────────────────────────────────


class JobSubmitRequest(BaseModel):
    """Request body for submitting a new file processing job."""

    job_type: JobType = Field(
        ...,
        description="Type of file processing to perform.",
        examples=["csv_summary"],
    )
    priority: JobPriority = Field(
        default=JobPriority.LOW,
        description="Queue priority. HIGH for interactive use, LOW for batch.",
    )
    payload: dict[str, Any] = Field(
        ...,
        description="Job input data. Must contain 'file_content' (base64) and 'filename'.",
        examples=[{"file_content": "dGVzdCBkYXRh", "filename": "data.csv"}],
    )


# ── Response DTOs ─────────────────────────────────────────────────────


class JobSubmitResponse(BaseModel):
    """Response returned when a job is successfully submitted (202 Accepted)."""

    job_id: str = Field(..., description="Unique job identifier (UUID).")
    status: JobStatus = Field(
        default=JobStatus.PENDING,
        description="Initial job status.",
    )
    priority: JobPriority = Field(..., description="Assigned priority.")
    message: str = Field(
        default="Job submitted successfully.",
        description="Human-readable confirmation.",
    )
    check_status_url: str = Field(
        ...,
        description="URL to poll for job status.",
        examples=["/jobs/550e8400-e29b-41d4-a716-446655440000"],
    )
    estimated_time: str = Field(
        default="5-15 seconds",
        description="Rough estimate for job completion.",
    )


class JobStatusResponse(BaseModel):
    """Response returned when polling a job's status."""

    job_id: str = Field(..., description="Unique job identifier.")
    status: JobStatus = Field(..., description="Current job status.")
    job_type: JobType = Field(..., description="Type of processing.")
    result: Optional[dict[str, Any]] = Field(
        default=None,
        description="Processing output (present when status is 'success').",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message (present when status is 'failed').",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="When the job was submitted.",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When the job finished (success, failed, or cancelled).",
    )
    retry_count: int = Field(
        default=0,
        description="Number of retry attempts so far.",
    )


class JobListResponse(BaseModel):
    """Response for listing recent jobs."""

    jobs: list[JobStatusResponse] = Field(
        default_factory=list,
        description="List of recent jobs.",
    )
    total: int = Field(..., description="Total number of jobs returned.")


# ── Monitoring DTOs ───────────────────────────────────────────────────


class QueueStatsResponse(BaseModel):
    """Response for queue statistics endpoint."""

    workers: dict[str, Any] = Field(
        default_factory=dict,
        description="Worker pool information.",
    )
    tasks: dict[str, Any] = Field(
        default_factory=dict,
        description="Active, scheduled, and reserved task counts.",
    )
    queue_depths: dict[str, int] = Field(
        default_factory=dict,
        description="Number of pending messages per queue.",
    )
    rate_limiting: dict[str, Any] = Field(
        default_factory=dict,
        description="Current rate limit usage per resource.",
    )


class HealthResponse(BaseModel):
    """Response for health check endpoint."""

    status: str = Field(
        ...,
        description="Overall health status: 'healthy' or 'unhealthy'.",
        examples=["healthy"],
    )
    components: dict[str, str] = Field(
        default_factory=dict,
        description="Per-component health status (redis, workers, queues).",
    )
