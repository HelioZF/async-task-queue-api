"""Image resize processor: decodes base64 image and resizes to max 800px."""

import base64
import io
import logging
from typing import Any

from PIL import Image

from src.domain.exceptions import ProcessingError
from src.domain.ports.file_processor import IFileProcessor
from src.domain.value_objects.enums import JobType

logger = logging.getLogger(__name__)

MAX_DIMENSION = 800


class ImageProcessor(IFileProcessor):
    """Processes images by resizing to fit within MAX_DIMENSION pixels."""

    @property
    def supported_job_type(self) -> JobType:
        return JobType.IMAGE_RESIZE

    def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            file_content = payload.get("file_content", "")
            if not file_content:
                raise ProcessingError("Missing file_content in payload", "image_resize")

            raw = base64.b64decode(file_content)
            img = Image.open(io.BytesIO(raw))

            original_size = {"width": img.width, "height": img.height}
            img_format = img.format or "PNG"

            # Resize if larger than MAX_DIMENSION
            if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
                img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

            new_size = {"width": img.width, "height": img.height}

            # Encode resized image back to base64
            buffer = io.BytesIO()
            save_format = img_format if img_format in ("PNG", "JPEG", "GIF") else "PNG"
            img.save(buffer, format=save_format)
            resized_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return {
                "original_size": original_size,
                "new_size": new_size,
                "format": save_format,
                "resized_content": resized_b64,
            }

        except ProcessingError:
            raise
        except Exception as e:
            logger.error("Image processing failed: %s", e)
            raise ProcessingError(f"Failed to process image: {e}", "image_resize")
