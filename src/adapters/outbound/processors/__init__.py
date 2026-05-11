"""Processor registry: maps JobType to IFileProcessor implementations."""

from src.domain.ports.file_processor import IFileProcessor
from src.domain.value_objects.enums import JobType

from .csv_processor import CsvProcessor
from .image_processor import ImageProcessor
from .pdf_processor import PdfProcessor
from .text_processor import TextProcessor

PROCESSOR_REGISTRY: dict[JobType, IFileProcessor] = {
    JobType.CSV_SUMMARY: CsvProcessor(),
    JobType.WORD_COUNT: TextProcessor(),
    JobType.IMAGE_RESIZE: ImageProcessor(),
    JobType.PDF_EXTRACT: PdfProcessor(),
}

__all__ = ["PROCESSOR_REGISTRY", "CsvProcessor", "TextProcessor", "ImageProcessor", "PdfProcessor"]
