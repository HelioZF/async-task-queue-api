"""Use case: List recent jobs."""

from src.domain.entities.job import Job
from src.domain.ports.job_store import IJobStore


class ListJobsUseCase:
    """Lists the most recently created jobs from the store."""

    def __init__(self, job_store: IJobStore):
        self._job_store = job_store

    def execute(self, limit: int = 20) -> list[Job]:
        return self._job_store.list_recent(limit=limit)
