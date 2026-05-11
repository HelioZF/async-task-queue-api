"""
Client library exceptions.

These exceptions are raised by TaskQueueClient methods
to signal error conditions to the caller.
"""


class ClientError(Exception):
    """Base exception for all client library errors."""

    pass


class JobTimeoutError(ClientError):
    """Raised when polling for a job result exceeds the timeout.

    Attributes:
        job_id: The UUID of the timed-out job.
        timeout: The timeout value in seconds.
    """

    def __init__(self, job_id: str, timeout: float):
        self.job_id = job_id
        self.timeout = timeout
        super().__init__(f"Job {job_id} timed out after {timeout}s")


class JobFailedError(ClientError):
    """Raised when a job completes with a failure status.

    Attributes:
        job_id: The UUID of the failed job.
        error_message: Human-readable error description.
        error_details: Additional error context (if available).
    """

    def __init__(
        self,
        job_id: str,
        error_message: str,
        error_details: dict | None = None,
    ):
        self.job_id = job_id
        self.error_message = error_message
        self.error_details = error_details or {}
        super().__init__(f"Job {job_id} failed: {error_message}")


class ApiConnectionError(ClientError):
    """Raised when the client cannot connect to the API.

    Attributes:
        base_url: The URL that was unreachable.
        original_error: The underlying connection error.
    """

    def __init__(self, base_url: str, original_error: Exception):
        self.base_url = base_url
        self.original_error = original_error
        super().__init__(f"Cannot connect to API at {base_url}: {original_error}")
