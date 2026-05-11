"""
Client library data models.

Plain dataclasses — no Pydantic, no external dependencies.
These represent the results returned to the caller.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class JobResult:
    """Result of a single job after polling completes.

    Attributes:
        job_id: Unique job identifier.
        status: Final status ("success", "failed", "cancelled").
        job_type: Type of processing that was performed.
        result: Processor output data (on success).
        error: Error message (on failure).
        created_at: When the job was submitted.
        completed_at: When the job finished.
        elapsed: Wall-clock seconds from submission to result retrieval.
    """

    job_id: str
    status: str
    job_type: str
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    elapsed: float = 0.0

    @property
    def is_success(self) -> bool:
        """True if the job completed successfully."""
        return self.status == "success"

    @property
    def is_failed(self) -> bool:
        """True if the job failed."""
        return self.status in ("failed", "FAILURE")


@dataclass
class BatchResult:
    """Aggregated result of a batch job submission.

    Attributes:
        total: Total number of jobs in the batch.
        succeeded: Number of jobs that completed successfully.
        failed: Number of jobs that failed.
        results: Individual results for each job.
        duration_seconds: Wall-clock time for the entire batch.
    """

    total: int
    succeeded: int
    failed: int
    results: list[JobResult] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        """Fraction of jobs that succeeded (0.0 to 1.0)."""
        if self.total == 0:
            return 0.0
        return self.succeeded / self.total

    @property
    def all_successful(self) -> bool:
        """True if every job in the batch succeeded."""
        return self.failed == 0 and self.total > 0
