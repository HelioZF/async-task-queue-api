"""Use case: Get the current status of a job."""

from src.domain.entities.job import Job
from src.domain.exceptions import JobNotFoundError
from src.domain.ports.job_store import IJobStore


class GetJobStatusUseCase:
    """Retrieves a job from the store by ID."""

    def __init__(self, job_store: IJobStore):
        self._job_store = job_store

    def execute(self, job_id: str) -> Job:
        job = self._job_store.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job
