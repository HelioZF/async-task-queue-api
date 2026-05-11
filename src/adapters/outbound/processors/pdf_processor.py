"""PDF text extraction processor: decodes base64 PDF and extracts text."""

import base64
import io
import logging
from typing import Any

import pdfplumber

from src.domain.exceptions import ProcessingError
from src.domain.ports.file_processor import IFileProcessor
from src.domain.value_objects.enums import JobType

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 5000


class PdfProcessor(IFileProcessor):
    """Processes PDF files and extracts text content."""

    @property
    def supported_job_type(self) -> JobType:
        return JobType.PDF_EXTRACT

    def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            file_content = payload.get("file_content", "")
            if not file_content:
                raise ProcessingError("Missing file_content in payload", "pdf_extract")

            raw = base64.b64decode(file_content)

            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                page_count = len(pdf.pages)
                all_text = ""

                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    all_text += page_text + "\n"

            total_chars = len(all_text.strip())
            extracted_text = all_text[:MAX_TEXT_LENGTH].strip()

            return {
                "page_count": page_count,
                "total_chars": total_chars,
                "extracted_text": extracted_text,
            }

        except ProcessingError:
            raise
        except Exception as e:
            logger.error("PDF processing failed: %s", e)
            raise ProcessingError(f"Failed to process PDF: {e}", "pdf_extract")
