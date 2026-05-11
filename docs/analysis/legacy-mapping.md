# Legacy-to-New File Mapping

> **Stage 0 — Code Analyst Agent**
> Complete file-by-file mapping from the legacy codebase to the new project.

---

## Legend

| Action | Meaning |
|--------|---------|
| **KEEP** | Pattern reusable as-is (rename only) |
| **ADAPT** | Structure reusable, content changes needed |
| **DISCARD** | Domain-specific, remove entirely |
| **REPLACE** | New implementation needed with same responsibility |

---

## Core Layer

| Legacy File | Action | New Project Target | Notes |
|---|---|---|---|
| `core/queue_config.py` | **ADAPT** | `src/infrastructure/config.py` | Merge with app config; rename queues to `jobs_high`/`jobs_low`; change prefix to `TASKQUEUE_`; add `redis_job_store_url` (DB 2) |
| `core/models/queue_models.py` | **ADAPT** | `src/domain/value_objects/enums.py` + `src/application/dtos/job_dtos.py` | Split enums (domain) from DTOs (application); rename Task→Job; add `JobType` enum and `CANCELLED` status |
| `core/models/errors.py` | **ADAPT** | `src/domain/exceptions.py` + `src/adapters/inbound/api/middleware.py` | Separate domain exceptions (no FastAPI imports) from HTTP handlers (adapter layer) |
| `core/models/common.py` | **DISCARD** | — | Contains Agent/Client models specific to legacy domain |
| `core/models/obligations.py` | **DISCARD** | — | Legacy domain models |
| `core/contracts/gateways.py` | **REPLACE** | `src/domain/ports/file_processor.py` + `src/domain/ports/job_store.py` | Keep ABC pattern; replace domain-specific interfaces with `IFileProcessor` and `IJobStore` |
| `core/__init__.py` | **DISCARD** | — | Empty init |
| `core/models/__init__.py` | **DISCARD** | — | Empty init |
| `core/contracts/__init__.py` | **DISCARD** | — | Empty init |

---

## Infrastructure Layer

| Legacy File | Action | New Project Target | Notes |
|---|---|---|---|
| `infrastructure/task_queue/celery_app.py` | **ADAPT** | `src/infrastructure/celery_app.py` | Rename app to `file_processing_api`; consolidate to 2 queues; remove Sentinel config |
| `infrastructure/task_queue/rate_limiter.py` | **KEEP** | `src/infrastructure/rate_limiter.py` | 100% generic — only change resource name defaults; consider DI instead of global singleton |
| `infrastructure/task_queue/tasks.py` | **ADAPT** | `src/infrastructure/celery_tasks.py` | Single `process_job` task replacing two legacy tasks; dispatcher to processor registry; remove pagination logic |
| `infrastructure/task_queue/__init__.py` | **DISCARD** | — | Empty init |
| `infrastructure/httpx_client/base.py` | **DISCARD** | — | Legacy HTTP client base with OAuth2 token management |
| `infrastructure/httpx_client/gateway.py` | **DISCARD** | — | Legacy API gateway with domain-specific methods |
| `infrastructure/httpx_client/__init__.py` | **DISCARD** | — | |
| `infrastructure/soap_client/base.py` | **DISCARD** | — | SOAP/WS-Security client |
| `infrastructure/soap_client/exceptions.py` | **DISCARD** | — | SOAP-specific exceptions |
| `infrastructure/soap_client/clients/measurements.py` | **DISCARD** | — | Legacy SOAP measurement client |
| `infrastructure/soap_client/clients/obligations.py` | **DISCARD** | — | Legacy SOAP obligation client |
| `infrastructure/soap_client/schemas/*.py` | **DISCARD** | — | Legacy SOAP XML schemas |
| `infrastructure/__init__.py` | **DISCARD** | — | Empty init |
| — (new) | **NEW** | `src/infrastructure/redis_client.py` | Redis connection factory for job store (DB 2) |
| — (new) | **NEW** | `src/adapters/outbound/redis_job_store.py` | Implements `IJobStore` — stores job metadata in Redis |
| — (new) | **NEW** | `src/adapters/outbound/processors/csv_processor.py` | Implements `IFileProcessor` for CSV (pandas) |
| — (new) | **NEW** | `src/adapters/outbound/processors/text_processor.py` | Implements `IFileProcessor` for text (stdlib) |
| — (new) | **NEW** | `src/adapters/outbound/processors/image_processor.py` | Implements `IFileProcessor` for images (Pillow) |
| — (new) | **NEW** | `src/adapters/outbound/processors/pdf_processor.py` | Implements `IFileProcessor` for PDFs (pdfplumber) |

---

## Web Layer (API Routes)

| Legacy File | Action | New Project Target | Notes |
|---|---|---|---|
| `web/queue/monitoring.py` | **ADAPT** | `src/adapters/inbound/api/monitoring_router.py` | Update queue names; update rate limit resources; remove legacy references |
| `web/queue/queue_management.py` | **ADAPT** | `src/adapters/inbound/api/jobs_router.py` | Rename `/tasks/` → `/jobs/`; add list endpoint; read from RedisJobStore + AsyncResult |
| `web/soap/measurements.py` | **DISCARD** | — | Legacy SOAP measurement endpoints |
| `web/soap/obligations.py` | **DISCARD** | — | Legacy SOAP obligation endpoints |
| `web/httpx/medicao.py` | **DISCARD** | — | Legacy HTTP measurement endpoints |
| `web/httpx/cadastro.py` | **DISCARD** | — | Legacy HTTP registration endpoints |
| `web/httpx/ccv.py` | **DISCARD** | — | Legacy HTTP CCV endpoints |
| `web/httpx/desconto.py` | **DISCARD** | — | Legacy HTTP discount endpoints |
| `web/httpx/notificacao.py` | **DISCARD** | — | Legacy HTTP notification endpoints |
| `web/test/auth.py` | **DISCARD** | — | Legacy auth testing endpoint |
| `web/queue/__init__.py` | **DISCARD** | — | Empty init |
| `web/soap/__init__.py` | **DISCARD** | — | Empty init |
| `web/httpx/__init__.py` | **DISCARD** | — | Empty init |
| — (new) | **NEW** | `src/adapters/inbound/api/middleware.py` | Error handling middleware, request logging |

---

## Application Entry Point

| Legacy File | Action | New Project Target | Notes |
|---|---|---|---|
| `main.py` | **ADAPT** | `src/main.py` | Keep CORS + exception handlers + validation handler; remove legacy routers; add jobs + monitoring routers; use app factory pattern |
| `config.py` | **ADAPT** | `src/infrastructure/config.py` | Remove legacy URLs, credentials, SSL paths; add file processing config; merge with queue config |

---

## Client Library

| Legacy File | Action | New Project Target | Notes |
|---|---|---|---|
| `ccee_queue_client/client.py` | **ADAPT** | `client/client.py` | Rename class; add `ThreadPoolExecutor`; add `submit_async()`, `submit_batch()` with Futures; add context manager; add exponential backoff |
| `ccee_queue_client/models.py` | **ADAPT** | `client/models.py` | Rename TaskResult → JobResult, BatchResult stays; add `elapsed` field; add `job_type` field; remove `results_by_index` (Futures handle ordering) |
| `ccee_queue_client/exceptions.py` | **ADAPT** | `client/exceptions.py` | Rename Task → Job; translate error messages to English; keep same structure |
| `ccee_queue_client/__init__.py` | **ADAPT** | `client/__init__.py` | Update exports |
| `ccee_queue_client/pyproject.toml` | **ADAPT** | `client/pyproject.toml` | Rename package; keep `requests` as only dependency |
| — (new) | **NEW** | `client/poller.py` | `_JobPoller` class with exponential backoff (0.5s → 5s cap); runs in background thread |

---

## Tests

| Legacy File | Action | New Project Target | Notes |
|---|---|---|---|
| `tests/conftest.py` | **REPLACE** | `tests/conftest.py` | New fixtures for test Redis, test Celery, test FastAPI client |
| `tests/unit/test_soap_endpoints.py` | **DISCARD** | — | Legacy SOAP tests |
| `tests/unit/test_httpx_endpoints.py` | **DISCARD** | — | Legacy HTTP tests |
| `tests/unit/test_auth_soap.py` | **DISCARD** | — | Legacy auth tests |
| `tests/unit/test_auth_httpx.py` | **DISCARD** | — | Legacy auth tests |
| `tests/integration/test_real_data.py` | **DISCARD** | — | Legacy integration tests with real API |
| `tests/e2e/test_api_full.py` | **DISCARD** | — | Legacy E2E tests |

---

## Docker & Config

| Legacy File | Action | New Project Target | Notes |
|---|---|---|---|
| `docker-compose.yml` | **ADAPT** | `docker-compose.yml` | Remove debug ports (5678/5679); remove cert volumes; consolidate workers (soap+httpx → high+low); add system deps for Pillow/pdfplumber |
| `requirements.txt` | **REPLACE** | `pyproject.toml` | Modern packaging; remove `xmltodict`; add `pandas`, `Pillow`, `pdfplumber` |
| — (new) | **NEW** | `Dockerfile` | Python 3.11-slim + system deps (libjpeg, libpng, poppler-utils) |
| — (new) | **NEW** | `Makefile` | `make up`, `make down`, `make logs`, `make test` |
| — (new) | **NEW** | `.env.example` | All `TASKQUEUE_` env vars with defaults |
| — (new) | **NEW** | `.dockerignore` | Exclude base/, .git, .venv, .pytest_cache |
| — (new) | **NEW** | `scripts/start-api.sh` | uvicorn startup |
| — (new) | **NEW** | `scripts/start-worker-high.sh` | Celery worker for jobs_high |
| — (new) | **NEW** | `scripts/start-worker-low.sh` | Celery worker for jobs_low |

---

## Other Files

| Legacy File | Action | New Project Target | Notes |
|---|---|---|---|
| `exemplo_cliente_api.py` | **DISCARD** | — | Legacy usage example |
| `testar_api.py` | **DISCARD** | — | Legacy test script |
| `run_integration_tests.py` | **DISCARD** | — | Legacy test runner |
| `scripts/verify_queue_serialization.py` | **DISCARD** | — | Legacy debug script |
| `.venv/` | **DISCARD** | — | Virtual environment (never commit) |

---

## Summary Statistics

| Action | Count |
|--------|-------|
| **KEEP** (as-is) | 1 |
| **ADAPT** (structure reuse) | 14 |
| **DISCARD** (remove) | 30 |
| **REPLACE** (new implementation) | 2 |
| **NEW** (no legacy equivalent) | 13 |
| **Total legacy files** | 47 |
| **Total new project files** | ~30 |

---

## Queue Name Mapping

| Legacy | New |
|--------|-----|
| `soap_high` | `jobs_high` |
| `soap_low` | `jobs_low` |
| `httpx_high` | _(removed)_ |
| `httpx_low` | _(removed)_ |

## Rate Limit Resource Mapping

| Legacy | New |
|--------|-----|
| `soap_api` (30 req/min) | `file_processing` (60 req/min) |
| `httpx_api` (60 req/min) | _(consolidated)_ |

## Environment Variable Prefix

| Legacy | New |
|--------|-----|
| `QUEUE_` | `TASKQUEUE_` |

---

## Security Flags

The following legacy files contain or reference sensitive data and must NEVER be carried into the new project:

| File | Issue |
|---|---|
| `config.py` | Contains credential fields (`ccee_username`, `ccee_password`, `ccee_soap_username`, `ccee_soap_password`) |
| `config.py` | Contains SSL certificate paths (`ssl_cert_path`, `ssl_key_path`) |
| `config.py` | Contains internal URLs (`ccee_httpx_base_url`, `ccee_soap_base_url`) |
| `docker-compose.yml` | Mounts `./cert` volume with SSL certificates |
| `.env` (if present) | Would contain actual credentials — must be in `.gitignore` |
