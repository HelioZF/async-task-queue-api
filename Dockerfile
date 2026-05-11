FROM python:3.11-slim

# System dependencies for Pillow and pdfplumber
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo-dev \
    libpng-dev \
    zlib1g-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir . 2>/dev/null || pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.27.0" \
    "celery[redis]>=5.4.0" \
    "redis>=5.0.0" \
    "flower>=2.0.0" \
    "pydantic>=2.0.0" \
    "pydantic-settings>=2.0.0" \
    "python-dotenv>=1.0.0" \
    "pandas>=2.0.0" \
    "Pillow>=10.0.0" \
    "pdfplumber>=0.10.0" \
    "loguru>=0.7.0" \
    "requests>=2.31.0"

# Copy application code
COPY src/ ./src/
COPY client/ ./client/

# Non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Default command (overridden by docker-compose)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
