"""
FastAPI application factory.

Creates and configures the application with routers,
exception handlers, and CORS middleware.
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src.adapters.inbound.api.jobs_router import router as jobs_router
from src.adapters.inbound.api.middleware import (
    domain_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
)
from src.adapters.inbound.api.monitoring_router import router as monitoring_router
from src.domain.exceptions import DomainError
from src.infrastructure.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.app_name,
        description=(
            "Asynchronous file processing API using FastAPI, Celery, and Redis. "
            "Supports CSV summary, word count, image resize, and PDF text extraction. "
            "Includes a multi-threaded Python client library."
        ),
        version=settings.app_version,
        debug=settings.debug,
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    application.add_exception_handler(DomainError, domain_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)

    # Routers
    application.include_router(jobs_router)
    application.include_router(monitoring_router)

    @application.get("/", tags=["Health"])
    async def root():
        return {
            "status": "ok",
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
        }

    return application


app = create_app()
