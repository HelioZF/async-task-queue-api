"""Use case: Cancel a pending or processing job."""

from src.domain.entities.job import Job
from src.domain.exceptions import JobNotFoundError
from src.domain.ports.job_store import IJobStore
from src.domain.value_objects.enums import JobStatus


class CancelJobUseCase:
    """Cancels a job by revoking its Celery task and updating the store."""

    def __init__(self, job_store: IJobStore):
        self._job_store = job_store

    def execute(self, job_id: str) -> Job:
        job = self._job_store.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id)

        if job.is_cancellable:
            from src.infrastructure.celery_app import celery_app

            celery_app.control.revoke(job_id, terminate=True)
            job.mark_cancelled()
            self._job_store.save(job)

        return job
