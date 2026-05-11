"""
Job poller with exponential backoff.

Encapsulates the poll-until-done loop that runs in a background thread.
Each poller instance gets its own requests.Session for thread safety.

Backoff schedule: 0.5s -> 1.0s -> 2.0s -> 4.0s -> 5.0s (capped)
"""

import logging
import time
from datetime import datetime, timezone

import requests

from .exceptions import ApiConnectionError, JobFailedError, JobTimeoutError
from .models import JobResult

logger = logging.getLogger(__name__)

# Terminal statuses that signal polling should stop
_TERMINAL_STATUSES = frozenset({"success", "failed", "cancelled", "SUCCESS", "FAILURE"})


class _JobPoller:
    """Polls a single job until completion, timeout, or failure.

    Each instance creates its own requests.Session for thread safety.
    Designed to be submitted to a ThreadPoolExecutor.

    Args:
        base_url: API base URL (e.g. "http://localhost:8000").
        job_id: UUID of the job to poll.
        job_type: The job type string (for result metadata).
        submit_time: When the job was submitted (for elapsed calculation).
        timeout: Max seconds to poll before raising JobTimeoutError.
        poll_interval: Initial interval between polls in seconds.
        max_poll_interval: Cap for exponential backoff in seconds.
    """

    def __init__(
        self,
        base_url: str,
        job_id: str,
        job_type: str,
        submit_time: float,
        timeout: float = 120.0,
        poll_interval: float = 0.5,
        max_poll_interval: float = 5.0,
    ):
        self._base_url = base_url
        self._job_id = job_id
        self._job_type = job_type
        self._submit_time = submit_time
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._max_poll_interval = max_poll_interval
        # Each poller gets its own session — thread-safe
        self._session = requests.Session()
        self._session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

    def poll(self) -> JobResult:
        """Block until the job reaches a terminal status or timeout.

        Returns:
            JobResult with the final job state.

        Raises:
            JobTimeoutError: If polling exceeds the timeout.
            JobFailedError: If the job fails.
            ApiConnectionError: If the API is unreachable.
        """
        current_interval = self._poll_interval
        start = time.monotonic()

        while True:
            elapsed_poll = time.monotonic() - start
            if elapsed_poll > self._timeout:
                raise JobTimeoutError(self._job_id, self._timeout)

            try:
                response = self._session.get(
                    f"{self._base_url}/jobs/{self._job_id}",
                    timeout=10,
                )
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.ConnectionError as e:
                raise ApiConnectionError(self._base_url, e)
            except requests.exceptions.HTTPError:
                # Transient error — wait and retry
                time.sleep(current_interval)
                current_interval = min(current_interval * 2, self._max_poll_interval)
                continue

            status = data.get("status", "").lower()

            if status in _TERMINAL_STATUSES:
                elapsed_total = time.time() - self._submit_time

                result = JobResult(
                    job_id=self._job_id,
                    status=status if status in ("success", "failed", "cancelled") else status,
                    job_type=data.get("job_type", self._job_type),
                    result=data.get("result"),
                    error=data.get("error"),
                    created_at=_parse_datetime(data.get("created_at")),
                    completed_at=_parse_datetime(data.get("completed_at")),
                    elapsed=round(elapsed_total, 2),
                )

                if result.is_failed:
                    raise JobFailedError(
                        job_id=self._job_id,
                        error_message=result.error or "Unknown error",
                    )

                return result

            # Not terminal — backoff and retry
            time.sleep(current_interval)
            current_interval = min(current_interval * 2, self._max_poll_interval)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO datetime string, returning None on failure."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
