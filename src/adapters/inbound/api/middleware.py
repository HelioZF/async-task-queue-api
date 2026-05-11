"""FastAPI exception handlers and middleware.

Maps domain exceptions to HTTP responses. Keeps domain layer
free from framework dependencies.
"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.domain.exceptions import (
    DomainError,
    InvalidPayloadError,
    JobCancelledError,
    JobNotFoundError,
    ProcessingError,
    RateLimitExceededError,
)

# Domain exception -> (HTTP status code, error code)
_EXCEPTION_MAP: dict[type, tuple[int, int]] = {
    JobNotFoundError: (404, 4004),
    InvalidPayloadError: (400, 4000),
    RateLimitExceededError: (429, 4029),
    ProcessingError: (500, 5001),
    JobCancelledError: (409, 4009),
}


async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handle domain exceptions with consistent JSON error format."""
    status_code, error_code = _EXCEPTION_MAP.get(type(exc), (500, 5000))
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": exc.message,
                "code": error_code,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "code": 5000,
                "detail": str(exc),
            }
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert Pydantic validation errors into readable messages."""
    missing = []
    invalid = []

    for error in exc.errors():
        field_name = error["loc"][-1] if error["loc"] else "unknown"
        error_type = error.get("type", "")

        if error_type == "missing":
            missing.append(field_name)
        else:
            msg = error.get("msg", "invalid value")
            invalid.append(f"'{field_name}': {msg}")

    parts = []
    if missing:
        names = ", ".join(f"'{f}'" for f in missing)
        parts.append(f"Missing required field(s): {names}")
    if invalid:
        parts.append("Invalid values: " + "; ".join(invalid))

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "message": ". ".join(parts) or "Validation error",
                "code": 4220,
            }
        },
    )
