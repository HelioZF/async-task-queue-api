"""Use case: Submit a new file processing job."""

from src.domain.entities.job import Job
from src.domain.ports.job_store import IJobStore
from src.domain.value_objects.enums import JobPriority, JobType


class SubmitJobUseCase:
    """Creates a Job entity, persists it, and dispatches it to Celery."""

    def __init__(self, job_store: IJobStore):
        self._job_store = job_store

    def execute(
        self,
        job_type: JobType,
        payload: dict,
        priority: JobPriority = JobPriority.LOW,
    ) -> Job:
        job = Job(
            job_type=job_type,
            priority=priority,
            payload=payload,
        )

        self._job_store.save(job)

        # Dispatch to Celery
        from src.infrastructure.celery_app import celery_app
        from src.infrastructure.config import settings

        queue = (
            settings.queue_jobs_high
            if priority == JobPriority.HIGH
            else settings.queue_jobs_low
        )

        celery_app.send_task(
            "src.infrastructure.celery_tasks.process_job",
            args=[job.job_id, job.job_type.value, job.payload],
            queue=queue,
            task_id=job.job_id,
        )

        return job
