"""
Multi-threaded Python client for the Async Task Queue API.

Provides three usage patterns:
  1. Sync:    client.submit_and_wait() — blocks until result
  2. Async:   client.submit_async()   — returns Future immediately
  3. Batch:   client.submit_batch()   — returns list of Futures

Threading model:
  - Main thread submits jobs via POST /jobs (fast, non-blocking)
  - Background threads in ThreadPoolExecutor poll for results
  - Each polling thread has its own requests.Session (thread-safe)

Example:
    with TaskQueueClient("http://localhost:8000") as client:
        future = client.submit_async("csv_summary", {"file_content": "...", "filename": "data.csv"})
        # Main thread is free to do other work
        result = future.result()  # blocks when needed
"""

import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

import requests

from .exceptions import ApiConnectionError, JobTimeoutError
from .models import BatchResult, JobResult
from .poller import _JobPoller

logger = logging.getLogger(__name__)


class TaskQueueClient:
    """Multi-threaded client for the Async Task Queue API.

    Args:
        base_url: API base URL (e.g. "http://localhost:8000").
        max_workers: Max threads in the polling pool.
        default_timeout: Default timeout in seconds for polling.
        poll_interval: Initial poll interval in seconds.
        max_poll_interval: Max poll interval cap in seconds.
    """

    def __init__(
        self,
        base_url: str,
        max_workers: int = 4,
        default_timeout: float = 120.0,
        poll_interval: float = 0.5,
        max_poll_interval: float = 5.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._default_timeout = default_timeout
        self._poll_interval = poll_interval
        self._max_poll_interval = max_poll_interval
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        # Main-thread session for job submission (fast POST calls)
        self._session = requests.Session()
        self._session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

    # ── Sync API ─────────────────────────────────────────────────────

    def submit_job(
        self,
        job_type: str,
        payload: dict[str, Any],
        priority: str = "low",
    ) -> str:
        """Submit a job and return the job_id immediately.

        Args:
            job_type: One of csv_summary, word_count, image_resize, pdf_extract.
            payload: Dict with file_content (base64) and filename.
            priority: "high" or "low".

        Returns:
            The job_id (UUID string).

        Raises:
            ApiConnectionError: If the API is unreachable.
        """
        body = {"job_type": job_type, "priority": priority, "payload": payload}
        try:
            response = self._session.post(
                f"{self._base_url}/jobs", json=body, timeout=10
            )
            response.raise_for_status()
            return response.json()["job_id"]
        except requests.exceptions.ConnectionError as e:
            raise ApiConnectionError(self._base_url, e)

    def get_status(self, job_id: str) -> JobResult:
        """Get the current status of a job (single poll, no waiting).

        Args:
            job_id: UUID of the job.

        Returns:
            JobResult with the current state.
        """
        response = self._session.get(
            f"{self._base_url}/jobs/{job_id}", timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return JobResult(
            job_id=data.get("job_id", job_id),
            status=data.get("status", "unknown"),
            job_type=data.get("job_type", ""),
            result=data.get("result"),
            error=data.get("error"),
        )

    def submit_and_wait(
        self,
        job_type: str,
        payload: dict[str, Any],
        priority: str = "low",
        timeout: float | None = None,
    ) -> JobResult:
        """Submit a job and block until the result is ready.

        Args:
            job_type: Type of processing.
            payload: Job input data.
            priority: Queue priority.
            timeout: Max seconds to wait (uses default if None).

        Returns:
            JobResult with the final state.

        Raises:
            JobTimeoutError: If polling exceeds timeout.
            JobFailedError: If the job fails.
        """
        timeout = timeout or self._default_timeout
        submit_time = time.time()
        job_id = self.submit_job(job_type, payload, priority)

        poller = _JobPoller(
            base_url=self._base_url,
            job_id=job_id,
            job_type=job_type,
            submit_time=submit_time,
            timeout=timeout,
            poll_interval=self._poll_interval,
            max_poll_interval=self._max_poll_interval,
        )
        try:
            return poller.poll()
        finally:
            poller.close()

    # ── Threaded Async API (Star Feature) ────────────────────────────

    def submit_async(
        self,
        job_type: str,
        payload: dict[str, Any],
        priority: str = "low",
        timeout: float | None = None,
    ) -> Future[JobResult]:
        """Submit a job and return a Future immediately.

        The job is submitted on the calling thread (fast POST).
        Polling runs in a background thread from the pool.
        The calling thread is free to do other work.

        Args:
            job_type: Type of processing.
            payload: Job input data.
            priority: Queue priority.
            timeout: Max seconds to poll (uses default if None).

        Returns:
            A Future[JobResult] that resolves when the job completes.
            Call .result() to block and get the JobResult.
            If the job fails, .result() raises JobFailedError.
            If timeout is exceeded, .result() raises JobTimeoutError.
        """
        timeout = timeout or self._default_timeout
        submit_time = time.time()
        job_id = self.submit_job(job_type, payload, priority)

        poller = _JobPoller(
            base_url=self._base_url,
            job_id=job_id,
            job_type=job_type,
            submit_time=submit_time,
            timeout=timeout,
            poll_interval=self._poll_interval,
            max_poll_interval=self._max_poll_interval,
        )

        return self._executor.submit(poller.poll)

    def submit_batch(
        self,
        jobs: list[tuple[str, dict[str, Any], str]],
        timeout: float | None = None,
    ) -> list[Future[JobResult]]:
        """Submit multiple jobs and return a list of Futures.

        Each job is submitted sequentially on the calling thread (fast).
        Each job gets its own polling thread from the pool.

        Args:
            jobs: List of (job_type, payload, priority) tuples.
            timeout: Max seconds per job (uses default if None).

        Returns:
            List of Future[JobResult], one per job, in submission order.
        """
        timeout = timeout or self._default_timeout
        futures: list[Future[JobResult]] = []

        for job_type, payload, priority in jobs:
            future = self.submit_async(job_type, payload, priority, timeout)
            futures.append(future)

        return futures

    # ── Health ────────────────────────────────────────────────────────

    def check_health(self) -> bool:
        """Check if the API is reachable and healthy.

        Returns:
            True if the API responds with a 200 on /health.
        """
        try:
            response = self._session.get(
                f"{self._base_url}/health", timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

    # ── Lifecycle ─────────────────────────────────────────────────────

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the thread pool and close HTTP sessions.

        Args:
            wait: If True, wait for all pending polling threads to finish.
        """
        self._executor.shutdown(wait=wait)
        self._session.close()

    def __enter__(self) -> "TaskQueueClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.shutdown()
