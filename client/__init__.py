"""
task-queue-client: Multi-threaded Python client for the Async Task Queue API.

Usage:
    from client import TaskQueueClient

    with TaskQueueClient("http://localhost:8000") as client:
        # Sync
        result = client.submit_and_wait("csv_summary", payload)

        # Async (non-blocking)
        future = client.submit_async("csv_summary", payload)
        result = future.result()

        # Batch
        futures = client.submit_batch([("csv_summary", payload, "high"), ...])
"""

from .client import TaskQueueClient
from .exceptions import ApiConnectionError, ClientError, JobFailedError, JobTimeoutError
from .models import BatchResult, JobResult

__all__ = [
    "TaskQueueClient",
    "JobResult",
    "BatchResult",
    "ClientError",
    "JobTimeoutError",
    "JobFailedError",
    "ApiConnectionError",
]
