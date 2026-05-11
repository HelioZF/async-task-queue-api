"""
Domain exceptions.

These exceptions represent domain-level error conditions.
They have zero framework dependencies — no FastAPI, no HTTP status codes.
Mapping to HTTP responses is the responsibility of the adapter layer.
"""


class DomainError(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str = "A domain error occurred"):
        self.message = message
        super().__init__(self.message)


class JobNotFoundError(DomainError):
    """Raised when a job ID does not exist in the store."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job not found: {job_id}")


class ProcessingError(DomainError):
    """Raised when a file processor fails to process input."""

    def __init__(self, message: str, job_type: str | None = None):
        self.job_type = job_type
        super().__init__(message)


class InvalidPayloadError(DomainError):
    """Raised when job input payload is malformed or missing required fields."""

    def __init__(self, message: str = "Invalid payload"):
        super().__init__(message)


class RateLimitExceededError(DomainError):
    """Raised when the rate limit for job submission is exceeded."""

    def __init__(self, resource: str = "file_processing"):
        self.resource = resource
        super().__init__(f"Rate limit exceeded for resource: {resource}")


class JobCancelledError(DomainError):
    """Raised when an operation is attempted on a cancelled job."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job has been cancelled: {job_id}")
