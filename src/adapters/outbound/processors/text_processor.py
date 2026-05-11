"""Word count processor: decodes base64 text and produces frequency analysis."""

import base64
import logging
import re
from collections import Counter
from typing import Any

from src.domain.exceptions import ProcessingError
from src.domain.ports.file_processor import IFileProcessor
from src.domain.value_objects.enums import JobType

logger = logging.getLogger(__name__)


class TextProcessor(IFileProcessor):
    """Processes text files and returns word frequency analysis."""

    @property
    def supported_job_type(self) -> JobType:
        return JobType.WORD_COUNT

    def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            file_content = payload.get("file_content", "")
            if not file_content:
                raise ProcessingError("Missing file_content in payload", "word_count")

            raw = base64.b64decode(file_content)
            text = raw.decode("utf-8")

            words = re.findall(r"\b[a-zA-Z]+\b", text.lower())

            if not words:
                return {
                    "total_words": 0,
                    "unique_words": 0,
                    "line_count": text.count("\n") + (1 if text else 0),
                    "top_10_words": [],
                }

            counter = Counter(words)
            top_10 = [
                {"word": word, "count": count}
                for word, count in counter.most_common(10)
            ]

            return {
                "total_words": len(words),
                "unique_words": len(counter),
                "line_count": text.count("\n") + 1,
                "top_10_words": top_10,
            }

        except ProcessingError:
            raise
        except Exception as e:
            logger.error("Text processing failed: %s", e)
            raise ProcessingError(f"Failed to process text: {e}", "word_count")
