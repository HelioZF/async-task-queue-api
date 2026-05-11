"""
Domain entity: Job.

A Job represents a file processing request submitted by a client.
It tracks the full lifecycle from submission through completion.

This is a plain dataclass — not a Pydantic model. Domain entities
must have zero framework dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from src.domain.value_objects.enums import JobPriority, JobStatus, JobType


@dataclass
class Job:
    """A file processing job in the system.

    Attributes:
        job_id: Unique identifier (UUID4).
        job_type: Type of file processing to perform.
        priority: Queue priority (determines which worker pool handles it).
        status: Current lifecycle status.
        payload: Input data containing file_content (base64) and filename.
        result: Processing output on success.
        error: Error message on failure.
        created_at: Timestamp when the job was submitted.
        completed_at: Timestamp when the job finished (success or failure).
        retry_count: Number of retry attempts so far.
        max_retries: Maximum allowed retries before permanent failure.
    """

    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_type: JobType = JobType.CSV_SUMMARY
    priority: JobPriority = JobPriority.LOW
    status: JobStatus = JobStatus.PENDING
    payload: dict[str, Any] = field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3

    def mark_processing(self) -> None:
        """Transition job to processing state."""
        self.status = JobStatus.PROCESSING

    def mark_success(self, result: dict[str, Any]) -> None:
        """Transition job to success state with result data."""
        self.status = JobStatus.SUCCESS
        self.result = result
        self.completed_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        """Transition job to failed state with error message."""
        self.status = JobStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(timezone.utc)

    def mark_cancelled(self) -> None:
        """Transition job to cancelled state."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)

    def increment_retry(self) -> bool:
        """Increment retry counter. Returns True if retries remain."""
        self.retry_count += 1
        return self.retry_count <= self.max_retries

    @property
    def is_terminal(self) -> bool:
        """Whether the job is in a final state (no further transitions)."""
        return self.status in (JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.CANCELLED)

    @property
    def is_cancellable(self) -> bool:
        """Whether the job can be cancelled."""
        return self.status in (JobStatus.PENDING, JobStatus.PROCESSING)
