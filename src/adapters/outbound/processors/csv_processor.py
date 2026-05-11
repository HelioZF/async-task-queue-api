"""CSV summary processor: decodes base64 CSV and produces statistics."""

import base64
import io
import logging
from typing import Any

import pandas as pd

from src.domain.exceptions import ProcessingError
from src.domain.ports.file_processor import IFileProcessor
from src.domain.value_objects.enums import JobType

logger = logging.getLogger(__name__)


class CsvProcessor(IFileProcessor):
    """Processes CSV files and returns row count, column stats, and preview."""

    @property
    def supported_job_type(self) -> JobType:
        return JobType.CSV_SUMMARY

    def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            file_content = payload.get("file_content", "")
            if not file_content:
                raise ProcessingError("Missing file_content in payload", "csv_summary")

            raw = base64.b64decode(file_content)
            df = pd.read_csv(io.BytesIO(raw))

            column_stats = {}
            for col in df.select_dtypes(include=["number"]).columns:
                column_stats[col] = {
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "mean": round(float(df[col].mean()), 2),
                }

            preview = df.head(5).to_dict(orient="records")

            return {
                "row_count": len(df),
                "columns": list(df.columns),
                "column_stats": column_stats,
                "preview": preview,
            }

        except ProcessingError:
            raise
        except Exception as e:
            logger.error("CSV processing failed: %s", e)
            raise ProcessingError(f"Failed to process CSV: {e}", "csv_summary")
