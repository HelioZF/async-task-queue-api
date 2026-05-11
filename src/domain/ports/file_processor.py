"""
Domain port: IFileProcessor.

Defines the contract for file processing adapters.
Each processor handles one job type (CSV, text, image, PDF)
and transforms raw input into structured output.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.domain.value_objects.enums import JobType


class IFileProcessor(ABC):
    """Interface for file processing adapters.

    Each implementation handles a specific JobType and converts
    a base64-encoded file payload into a structured result dict.
    """

    @property
    @abstractmethod
    def supported_job_type(self) -> JobType:
        """The job type this processor handles."""
        ...

    @abstractmethod
    def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process a file and return structured results.

        Args:
            payload: Dict containing at minimum:
                - file_content (str): Base64-encoded file content.
                - filename (str): Original filename with extension.

        Returns:
            Dict with processor-specific result data.

        Raises:
            ProcessingError: If the file cannot be processed.
        """
        ...
