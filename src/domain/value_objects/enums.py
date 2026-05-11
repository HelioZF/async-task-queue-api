"""
Domain value objects: enumerations for job lifecycle.

These enums define the bounded vocabulary of the domain.
They inherit from (str, Enum) for JSON serialization compatibility
with Celery's JSON serializer and Pydantic v2.
"""

from enum import Enum


class JobStatus(str, Enum):
    """Status of a job throughout its lifecycle."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(str, Enum):
    """Priority level for job queue routing.

    HIGH: Routed to jobs_high queue (4 workers, faster processing).
    LOW: Routed to jobs_low queue (2 workers, background processing).
    """

    LOW = "low"
    HIGH = "high"


class JobType(str, Enum):
    """Supported file processing job types."""

    CSV_SUMMARY = "csv_summary"
    WORD_COUNT = "word_count"
    IMAGE_RESIZE = "image_resize"
    PDF_EXTRACT = "pdf_extract"
