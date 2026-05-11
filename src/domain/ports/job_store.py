"""
Domain port: IJobStore.

Defines the contract for job persistence.
The implementation is storage-agnostic — the domain doesn't know
whether jobs are stored in Redis, a database, or memory.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities.job import Job
from src.domain.value_objects.enums import JobStatus


class IJobStore(ABC):
    """Interface for job metadata persistence.

    Implementations must handle serialization, TTL management,
    and concurrent access safely.
    """

    @abstractmethod
    def save(self, job: Job) -> None:
        """Persist a job (create or overwrite).

        Args:
            job: The job entity to store.
        """
        ...

    @abstractmethod
    def get(self, job_id: str) -> Optional[Job]:
        """Retrieve a job by its ID.

        Args:
            job_id: UUID of the job.

        Returns:
            The Job entity if found, None otherwise.
        """
        ...

    @abstractmethod
    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update a job's status and optionally its result or error.

        Args:
            job_id: UUID of the job.
            status: New status to set.
            result: Processing result data (on success).
            error: Error message (on failure).
        """
        ...

    @abstractmethod
    def list_recent(self, limit: int = 20) -> list[Job]:
        """List the most recently created jobs.

        Args:
            limit: Maximum number of jobs to return.

        Returns:
            List of Job entities, ordered by created_at descending.
        """
        ...

    @abstractmethod
    def delete(self, job_id: str) -> bool:
        """Delete a job from the store.

        Args:
            job_id: UUID of the job.

        Returns:
            True if the job was found and deleted, False otherwise.
        """
        ...
