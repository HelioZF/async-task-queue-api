# Project 1 — Async Task Queue API
## Agent-Pipeline Implementation Plan

> **This plan replaces the original `IMPLEMENTATION_PLAN.md`** (7 technical phases) with a 10-stage agent-driven pipeline aligned to the [Project 4 AI Agent Orchestration Framework](../../project4_ai-agent-orchestration-framework).

---

## Overview

**Goal:** Rebuild the CCEE legacy code as a generic **File Processing API** with a multi-threaded Python client library, driven entirely by the Project 4 agent pipeline.

**Domain:** File processing — CSV summary, word count, image resize, PDF text extraction.

**Tech Stack:** FastAPI + Celery + Redis (no SQL database), Pydantic v2, Loguru, Docker Compose, Flower.

**Star Feature:** Multi-threaded client library with `concurrent.futures.ThreadPoolExecutor` and `Future`-based async API.

---

## Adaptations from Project 4's Standard Pipeline

| Project 4 Standard | Project 1 Adaptation |
|---|---|
| Backend creates SQLAlchemy models | Skipped — no SQL database |
| Backend creates Alembic migrations | Skipped — no schema migrations |
| Backend creates database repositories | Replaced with `RedisJobStore` (same port pattern) |
| Single Backend stage | Split into **3 stages** (Core, Client Lib, Demos) |
| Code Analyst finds bugs | Repurposed to extract reusable patterns |
| QA runs once | Split into **2 stages** (Tests + Final Validation) |

---

## Stage Dependency Graph

```
Stage 0: Code Analyst ──→ Stage 1: Planner
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            Stage 2: Backend      Stage 3: Backend
            (Core + API)          (Client Library)
                    │                   │
                    ▼                   │
            Stage 4: Deploy             │
                    │                   │
                    ├───────────────────┤
                    ▼                   ▼
            Stage 5: QA           Stage 6: Backend
            (Tests)               (Demos + Examples)
                    │                   │
                    └─────────┬─────────┘
                              ▼
                    Stage 7: Docs Agent
                              │
                              ▼
                    Stage 8: QA (Final Validation)
                              │
                              ▼
                    Stage 9: Process (Retrospective)
```

**Parallelizable pairs:** Stages 2+3 | Stages 5+6

---

## Target Project Structure

```
async-task-queue-api/
├── src/
│   ├── domain/                          # Stage 1 (Planner)
│   │   ├── entities/job.py
│   │   ├── value_objects/enums.py
│   │   ├── ports/
│   │   │   ├── file_processor.py
│   │   │   └── job_store.py
│   │   └── exceptions.py
│   ├── application/
│   │   ├── dtos/job_dtos.py             # Stage 1 (Planner)
│   │   ├── use_cases/                   # Stage 2 (Backend)
│   │   │   ├── submit_job.py
│   │   │   ├── get_job_status.py
│   │   │   ├── cancel_job.py
│   │   │   └── list_jobs.py
│   │   └── mappers/job_mapper.py        # Stage 2 (Backend)
│   ├── adapters/
│   │   ├── inbound/api/                 # Stage 2 (Backend)
│   │   │   ├── jobs_router.py
│   │   │   ├── monitoring_router.py
│   │   │   └── middleware.py
│   │   └── outbound/                    # Stage 2 (Backend)
│   │       ├── redis_job_store.py
│   │       └── processors/
│   │           ├── csv_processor.py
│   │           ├── text_processor.py
│   │           ├── image_processor.py
│   │           ├── pdf_processor.py
│   │           └── __init__.py          # Processor registry
│   ├── infrastructure/                  # Stage 2 (Backend)
│   │   ├── config.py
│   │   ├── redis_client.py
│   │   ├── celery_app.py
│   │   ├── celery_tasks.py
│   │   └── rate_limiter.py
│   └── main.py                          # Stage 2 (Backend)
├── client/                              # Stage 3 (Backend - Star Feature)
│   ├── __init__.py
│   ├── client.py
│   ├── poller.py
│   ├── models.py
│   ├── exceptions.py
│   └── pyproject.toml
├── examples/                            # Stage 6 (Backend)
│   ├── demo_simple.py
│   ├── demo_multithreaded.py
│   ├── demo_batch.py
│   ├── sample_files/
│   └── README.md
├── tests/                               # Stage 5 (QA)
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── conftest.py
├── docs/
│   ├── analysis/                        # Stage 0 (Code Analyst)
│   ├── planning/                        # Stage 1 (Planner)
│   ├── human/                           # Stage 7 (Docs)
│   ├── ai/                              # Stage 7 (Docs)
│   └── qa_reports/                      # Stages 5, 8, 9
├── scripts/                             # Stage 4 (Deploy)
├── Dockerfile                           # Stage 4 (Deploy)
├── docker-compose.yml                   # Stage 4 (Deploy)
├── pyproject.toml                       # Stage 2 (Backend)
├── Makefile                             # Stage 4 (Deploy)
├── .env.example                         # Stage 4 (Deploy)
├── .gitignore                           # Stage 4 (Deploy)
└── README.md                            # Stage 7 (Docs)
```

---

## Stage 0 — Code Analyst Agent (Legacy Analysis)

### Summary
| Field | Value |
|---|---|
| **Agent** | Code Analyst |
| **Window** | PERSISTENT |
| **Depends on** | Nothing (first stage) |
| **Produces** | `docs/analysis/legacy-patterns.md`, `docs/analysis/legacy-mapping.md` |
| **Write scope** | `docs/analysis/` |

### Seed Prompt

```
You are the Code Analyst Agent for Project 1 (Async Task Queue API - File Processing).

## YOUR TASK
Analyze the legacy codebase in `base/api_ccee/` and produce structured analysis documents.
You NEVER modify code.

## WHAT TO ANALYZE

1. **Reusable patterns** — Extract the architectural patterns, NOT the business logic:
   - Celery app configuration (infrastructure/task_queue/celery_app.py)
   - Rate limiter with sliding window + fail-open (infrastructure/task_queue/rate_limiter.py)
   - Task retry logic with exponential backoff + jitter (infrastructure/task_queue/tasks.py)
   - Priority queue routing (high/low queues) (celery_app.py task_routes + queue_config.py)
   - Pydantic models for task status/response (core/models/queue_models.py)
   - Health check + monitoring endpoints (web/queue/monitoring.py)
   - Task status polling + cancellation (web/queue/queue_management.py)
   - Docker Compose orchestration (docker-compose.yml)
   - Client library architecture (ccee_queue_client/ — client.py, models.py, exceptions.py)
   - Port/contract pattern (core/contracts/gateways.py)
   - Pydantic Settings configuration (config.py, core/queue_config.py)

2. **What to discard** — Identify CCEE-specific elements that must NOT carry over:
   - SOAP client, mTLS, WS-Security, certificates
   - CCEE domain models (obligations, measurements, agents)
   - Auto-pagination logic for CCEE API responses
   - All references to "CCEE", "Lux", "Lux Energia"
   - Portuguese-language variable names and docstrings (new project uses English)

3. **Client library gap analysis** — The legacy client (ccee_queue_client/) is
   synchronous-only with sequential batch polling. The new client must add:
   - concurrent.futures.ThreadPoolExecutor for non-blocking polling
   - submit_async() returning Future[JobResult]
   - submit_batch() returning list[Future[JobResult]]
   - Exponential backoff polling (0.5s -> 1s -> 2s -> 5s cap)
   - Thread-safe HTTP sessions (one requests.Session per thread)
   - Context manager support (__enter__/__exit__)

## OUTPUT FORMAT

Write two files:

### docs/analysis/legacy-patterns.md
For each reusable pattern:
- Pattern name
- Source file(s) in base/api_ccee/
- Code snippet showing the pattern
- Adaptation notes (what changes for the new project)
- Target file in new project

### docs/analysis/legacy-mapping.md
Table format:
| Legacy File | Keep/Discard/Adapt | New Project Target | Notes |

## CRITICAL RULES
- NEVER modify any source code
- NEVER reference "CCEE", "Lux", or proprietary details in your output
- Focus on PATTERNS, not business logic
- Flag any file that contains credentials or secrets
```

### Acceptance Criteria
- [ ] `docs/analysis/legacy-patterns.md` covers all 11 pattern areas
- [ ] `docs/analysis/legacy-mapping.md` maps every file in `base/api_ccee/`
- [ ] No CCEE/Lux references in output documents
- [ ] Client library gap analysis identifies sync-only limitation and threading requirements

---

## Stage 1 — Planner Agent (Domain Foundation)

### Summary
| Field | Value |
|---|---|
| **Agent** | Planner |
| **Window** | PERSISTENT |
| **Depends on** | Stage 0 |
| **Produces** | `src/domain/`, `src/application/dtos/`, `docs/planning/` |
| **Write scope** | `src/domain/`, `src/application/dtos/`, `docs/planning/` |

### Seed Prompt

```
You are the Planner Agent for Project 1 (Async Task Queue API - File Processing).

## YOUR TASK
Define the complete domain layer and API contracts for a file processing async job queue.

## CONTEXT
Read these files first:
- docs/analysis/legacy-patterns.md — reusable patterns from legacy code
- docs/analysis/legacy-mapping.md — legacy to new project mapping
- planner/IMPLEMENTATION_PLAN.md — original plan (sections 1, 5, 6, 8 for models, API, client)

## DOMAIN OVERVIEW

This is a file processing service. Clients submit jobs (CSV summary, word count, image resize,
PDF extract) via REST API. Jobs are queued by priority (high/low) and processed by background
workers. Results are stored in Redis with 1-hour TTL.

There is NO SQL database. Redis is the only data store (message broker + result backend).

## WHAT TO CREATE

### 1. src/domain/entities/job.py
A Job dataclass (NOT Pydantic) representing a job in the system:
- job_id: str (UUID)
- job_type: JobType
- priority: JobPriority
- status: JobStatus
- payload: dict (file_content as base64, filename)
- result: Optional[dict]
- error: Optional[str]
- created_at: datetime
- completed_at: Optional[datetime]
- retry_count: int = 0
- max_retries: int = 3

### 2. src/domain/value_objects/enums.py
- JobStatus(str, Enum): pending, processing, success, failed, cancelled
- JobPriority(str, Enum): low, high
- JobType(str, Enum): csv_summary, word_count, image_resize, pdf_extract

### 3. src/domain/ports/file_processor.py
ABC IFileProcessor with:
- process(payload: dict) -> dict — process file, return result dict
- supported_job_type: JobType — class attribute

### 4. src/domain/ports/job_store.py
ABC IJobStore with:
- save(job: Job) -> None
- get(job_id: str) -> Optional[Job]
- update_status(job_id: str, status: JobStatus, result: Optional[dict] = None,
  error: Optional[str] = None) -> None
- list_recent(limit: int = 20) -> list[Job]
- delete(job_id: str) -> bool

### 5. src/domain/exceptions.py
- DomainError(Exception) — base
- JobNotFoundError(DomainError) — job_id not found in store
- ProcessingError(DomainError) — file processor error
- RateLimitExceededError(DomainError) — rate limit hit
- JobCancelledError(DomainError) — job was cancelled
- InvalidPayloadError(DomainError) — bad input data

### 6. src/application/dtos/job_dtos.py
Pydantic v2 models:
- JobSubmitRequest: job_type (JobType), priority (JobPriority, default low),
  payload (dict with file_content and filename)
- JobSubmitResponse: job_id, status, priority, message, check_status_url, estimated_time
- JobStatusResponse: job_id, status, job_type, result (optional), error (optional),
  created_at, completed_at
- JobListResponse: jobs (list of JobStatusResponse), total (int)
- QueueStatsResponse: workers (dict), tasks (dict), queue_depths (dict), rate_limiting (dict)
- HealthResponse: status (str), components (dict)

### 7. docs/planning/domain-model.md
Document the domain model with a Mermaid class diagram showing entities, value objects,
ports, and their relationships.

### 8. docs/planning/api-contract.md
Document all API endpoints with request/response examples:
- POST /jobs (submit) -> 202
- GET /jobs/{job_id} (status) -> 200
- DELETE /jobs/{job_id} (cancel) -> 200
- GET /jobs (list recent) -> 200
- GET /health -> 200
- GET /queue/stats -> 200

## WRITE SCOPE
You may ONLY write to:
- src/domain/
- src/application/dtos/
- docs/planning/

## CRITICAL RULES
- Entities are dataclasses, NOT Pydantic models
- DTOs are Pydantic v2 BaseModel
- Ports are ABCs with @abstractmethod
- NEVER implement use cases, mappers, or adapters
- NEVER write SQLAlchemy models (there is no SQL database)
- NEVER write FastAPI routes
- NEVER write Celery tasks
- All code in English, all docstrings in English
- Include __init__.py for every package with proper __all__ exports
```

### Acceptance Criteria
- [ ] All 6 source files exist and are syntactically valid Python
- [ ] `Job` is a `@dataclass`, not a Pydantic model
- [ ] `IFileProcessor` and `IJobStore` are ABCs with `@abstractmethod`
- [ ] DTOs use Pydantic v2 `BaseModel` with proper field validation
- [ ] No implementation code (no use cases, no adapters)
- [ ] `docs/planning/` contains both documents with Mermaid diagrams
- [ ] Enums: 5 statuses, 2 priorities, 4 job types

---

## Stage 2 — Backend Agent (Core Infrastructure + API)

### Summary
| Field | Value |
|---|---|
| **Agent** | Backend |
| **Window** | PERSISTENT |
| **Depends on** | Stage 1 |
| **Produces** | `src/infrastructure/`, `src/adapters/`, `src/application/use_cases/`, `src/application/mappers/`, `src/main.py`, `pyproject.toml` |
| **Write scope** | `src/application/use_cases/`, `src/application/mappers/`, `src/adapters/`, `src/infrastructure/`, `src/main.py`, `pyproject.toml` |

### Seed Prompt

```
You are the Backend Agent for Project 1 (Async Task Queue API - File Processing).

## YOUR TASK
Implement the complete application layer, adapter layer, and infrastructure layer for a file
processing async job queue API.

## CONTEXT
Read these files first:
- src/domain/ — ALL files (entities, ports, value objects, exceptions) — READ ONLY
- src/application/dtos/ — ALL DTOs — READ ONLY
- docs/analysis/legacy-patterns.md — patterns to adapt from legacy code
- docs/planning/api-contract.md — API contract specification

## ARCHITECTURE

Hexagonal architecture:
- Domain (READ ONLY): entities, ports, value objects, exceptions
- Application (you build): use cases, mappers
- Adapters (you build): inbound (FastAPI routes) and outbound (Redis store, file processors)
- Infrastructure (you build): Celery, Redis connection, config, rate limiter

Key constraint: NO SQL DATABASE. Redis is the only data store.
- Message broker: Redis DB 0
- Result backend: Redis DB 1
- Job metadata store: Redis DB 2 (managed via RedisJobStore)

## WHAT TO IMPLEMENT

### Infrastructure Layer

1. src/infrastructure/config.py — Pydantic Settings:
   - app_name, app_version, debug
   - redis_url (default: redis://localhost:6379/0)
   - redis_result_backend (redis://localhost:6379/1)
   - redis_job_store_url (redis://localhost:6379/2)
   - rate_limit_max_requests: int = 60 (per minute)
   - job_result_ttl: int = 3600 (1 hour)
   - celery_task_soft_time_limit: int = 300
   - celery_task_time_limit: int = 360
   - worker_prefetch_multiplier: int = 1
   - worker_max_tasks_per_child: int = 100
   - Load from .env with env_prefix = "TASKQUEUE_"

2. src/infrastructure/redis_client.py — Connection factory, lazy singleton

3. src/infrastructure/celery_app.py — Adapt from legacy pattern:
   - Two queues: jobs_high, jobs_low
   - JSON serialization
   - task_track_started=True, task_acks_late=True
   - Auto-discover tasks from src.infrastructure

4. src/infrastructure/rate_limiter.py — Adapt sliding window from legacy:
   - Same algorithm (sorted set + pipeline)
   - Fail-open on Redis errors
   - Generalized resource names

5. src/infrastructure/celery_tasks.py — Single generic task process_job:
   - Receives job_id, job_type, payload
   - Updates job status to PROCESSING via IJobStore
   - Dispatches to correct processor via registry
   - On success: updates job to SUCCESS with result
   - On failure: retries up to 3x with exponential backoff + jitter, then FAILED
   - Rate-limited via RateLimiter

### Adapter Layer — Outbound

6. src/adapters/outbound/redis_job_store.py — Implements IJobStore:
   - Store Job as JSON hash in Redis with TTL
   - Key pattern: job:{job_id}
   - Maintain a sorted set jobs:recent (score=created_at timestamp) for list_recent()
   - Handle redis.RedisError gracefully

7. src/adapters/outbound/processors/ — Four processors implementing IFileProcessor:
   - csv_processor.py: Decode base64 -> pandas DataFrame -> {row_count, columns, column_stats, preview}
   - text_processor.py: Decode base64 -> count words -> {total_words, unique_words, top_10_words, line_count}
   - image_processor.py: Decode base64 -> Pillow resize to max 800px -> {original_size, new_size, format, resized_content}
   - pdf_processor.py: Decode base64 -> pdfplumber -> {page_count, total_chars, extracted_text}
   - __init__.py: PROCESSOR_REGISTRY: dict[JobType, IFileProcessor]

### Application Layer

8. Use cases (each in own file):
   - SubmitJobUseCase: Create Job, save to store, dispatch Celery task, return JobSubmitResponse
   - GetJobStatusUseCase: Load from store, map to JobStatusResponse
   - CancelJobUseCase: Revoke Celery task, update store to CANCELLED
   - ListJobsUseCase: Load recent from store, map to JobListResponse

9. src/application/mappers/job_mapper.py: Job -> JobStatusResponse, Job + queue -> JobSubmitResponse

### Adapter Layer — Inbound

10. src/adapters/inbound/api/jobs_router.py:
    - POST /jobs -> 202 Accepted (rate-limited)
    - GET /jobs/{job_id} -> 200
    - DELETE /jobs/{job_id} -> 200
    - GET /jobs -> 200 (list recent)

11. src/adapters/inbound/api/monitoring_router.py:
    - GET /health -> Redis ping, worker check
    - GET /queue/stats -> queue depths, worker stats, rate limit status

12. src/adapters/inbound/api/middleware.py:
    - Exception handler mapping domain exceptions to HTTP status codes
    - Request ID injection (UUID per request)
    - Structured logging with Loguru

13. src/main.py: FastAPI app factory, include routers, dependency injection wiring

14. pyproject.toml: All dependencies (fastapi, celery, redis, pydantic, pydantic-settings,
    loguru, pandas, Pillow, pdfplumber, flower, requests, httpx, pytest, pytest-asyncio)

## WRITE SCOPE
You may ONLY write to:
- src/application/use_cases/
- src/application/mappers/
- src/adapters/
- src/infrastructure/
- src/main.py
- pyproject.toml

## CRITICAL RULES
- NEVER modify files in src/domain/ or src/application/dtos/
- NEVER write Alembic migrations (no SQL database)
- NEVER write SQLAlchemy models
- Use dependency injection: use cases receive ports (interfaces), not concrete implementations
- All docstrings in English
- The process_job Celery task must be the ONLY Celery task — it dispatches to processors by job_type
- Rate limiter must fail-open (allow request if Redis is down)
```

### Acceptance Criteria
- [ ] `POST /jobs` returns 202 with `job_id`
- [ ] `GET /jobs/{job_id}` shows status transitions (pending -> processing -> success)
- [ ] All 4 processors produce correct output for valid input
- [ ] Rate limiter blocks excessive requests and fails open on Redis errors
- [ ] `GET /health` returns component health
- [ ] `GET /queue/stats` returns live metrics
- [ ] Use cases depend only on ports (ABCs), never on concrete implementations
- [ ] No files modified in `src/domain/` or `src/application/dtos/`

---

## Stage 3 — Backend Agent (Client Library) ⭐ Star Feature

### Summary
| Field | Value |
|---|---|
| **Agent** | Backend |
| **Window** | PERSISTENT |
| **Depends on** | Stage 1 (API contracts only) |
| **Produces** | `client/` standalone package |
| **Write scope** | `client/` |

### Seed Prompt

```
You are the Backend Agent for Project 1. This is a DEDICATED STAGE for the client library.

## YOUR TASK
Build a multi-threaded Python client library for the Async Task Queue API. This is the
STAR FEATURE of the project — it demonstrates real-world patterns for non-blocking batch
job processing.

## CONTEXT
Read these files:
- docs/planning/api-contract.md — the API your client will talk to
- src/application/dtos/job_dtos.py — response shapes from the API
- docs/analysis/legacy-patterns.md — legacy client patterns (synchronous-only)

## LEGACY ANALYSIS
The legacy client (base/api_ccee/ccee_queue_client/) is synchronous-only:
- submit_task() -> task_id
- wait_for_task() -> blocks with sequential polling
- batch_submit_and_wait() -> submits all, then polls sequentially

Your client adds THREADING:
- submit_async() -> returns Future[JobResult], polling runs in background thread
- submit_batch() -> each job gets its own polling thread from ThreadPoolExecutor
- Main thread stays free immediately

## WHAT TO BUILD

### 1. client/exceptions.py
- ClientError(Exception) — base
- JobTimeoutError(ClientError) — with job_id, timeout fields
- JobFailedError(ClientError) — with job_id, error_message, error_details
- ApiConnectionError(ClientError) — with base_url, original_error

### 2. client/models.py

@dataclass
class JobResult:
    job_id: str
    status: str                  # "success", "failed", "cancelled"
    job_type: str
    result: dict | None          # Processor output on success
    error: str | None            # Error message on failure
    created_at: datetime | None
    completed_at: datetime | None
    elapsed: float               # Seconds from submit to result

    @property
    def is_success(self) -> bool: ...
    @property
    def is_failed(self) -> bool: ...

@dataclass
class BatchResult:
    total: int
    succeeded: int
    failed: int
    results: list[JobResult]
    duration_seconds: float

    @property
    def success_rate(self) -> float: ...
    @property
    def all_successful(self) -> bool: ...

### 3. client/poller.py
_JobPoller encapsulates the poll-until-done loop:
- Constructor: __init__(self, session, base_url, job_id, timeout, poll_interval, max_poll_interval)
- poll() -> JobResult — blocking poll loop with exponential backoff
- Backoff: starts at poll_interval (0.5s), doubles each, caps at max_poll_interval (5.0s)
- On timeout: raises JobTimeoutError
- On failure status: raises JobFailedError
- Thread-safe: uses its own requests.Session instance (NOT shared)

### 4. client/client.py

class TaskQueueClient:
    def __init__(self, base_url, max_workers=4, default_timeout=120,
                 poll_interval=0.5, max_poll_interval=5.0): ...

    # --- Sync API ---
    def submit_job(self, job_type, payload, priority="low") -> str:
        """POST /jobs -> return job_id"""

    def get_status(self, job_id) -> JobResult:
        """GET /jobs/{job_id} -> single poll"""

    def submit_and_wait(self, job_type, payload, priority="low", timeout=120) -> JobResult:
        """Submit + block until result"""

    # --- Threaded API (STAR FEATURE) ---
    def submit_async(self, job_type, payload, priority="low", timeout=120) -> Future[JobResult]:
        """Submit, return Future immediately. Polling in background thread."""

    def submit_batch(self, jobs: list[tuple[str, dict, str]]) -> list[Future[JobResult]]:
        """Submit multiple jobs. Each gets its own polling thread."""

    # --- Health ---
    def check_health(self) -> bool

    # --- Lifecycle ---
    def shutdown(self, wait=True): ...
    def __enter__(self): return self
    def __exit__(self, *args): self.shutdown()

### 5. client/pyproject.toml
Minimal: name=task-queue-client, version=0.1.0, dependencies=[requests>=2.31]

## KEY IMPLEMENTATION DETAILS
- ThreadPoolExecutor created in __init__ with max_workers
- Thread-safe sessions: each polling thread gets its own requests.Session
- submit_async flow: POST /jobs on main thread -> create _JobPoller -> executor.submit(poller.poll) -> return Future
- submit_batch flow: POST /jobs for each (on main thread) -> create pollers -> submit all to executor -> return Futures
- Exponential backoff: 0.5 -> 1.0 -> 2.0 -> 4.0 -> 5.0 (capped)
- Timeout: wall-clock time from when polling starts

## WRITE SCOPE
You may ONLY write to client/

## CRITICAL RULES
- STANDALONE package — NO imports from src/
- Only dependency is requests (no fastapi, celery, redis)
- models.py uses plain dataclasses, not Pydantic
- Thread safety is paramount — no shared mutable state between threads
- Every public method has a docstring with Args/Returns/Raises
- Exponential backoff MUST cap at max_poll_interval
```

### Acceptance Criteria
- [ ] `client/` is standalone with only `requests` as dependency
- [ ] `submit_async()` returns `Future[JobResult]` without blocking
- [ ] `submit_batch()` returns N Futures for N jobs
- [ ] Exponential backoff: 0.5 -> 1.0 -> 2.0 -> 4.0 -> 5.0 (capped)
- [ ] `JobTimeoutError` raised after timeout seconds
- [ ] `shutdown()` terminates `ThreadPoolExecutor`
- [ ] Context manager works: `with TaskQueueClient(url) as client: ...`
- [ ] No imports from `src/`

---

## Stage 4 — Deploy Agent (Docker + Infrastructure)

### Summary
| Field | Value |
|---|---|
| **Agent** | Deploy |
| **Window** | EPHEMERAL |
| **Depends on** | Stage 2 |
| **Produces** | `Dockerfile`, `docker-compose.yml`, `.env.example`, `.gitignore`, `scripts/`, `Makefile` |
| **Write scope** | `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`, `.gitignore`, `scripts/`, `Makefile` |

### Seed Prompt

```
You are the Deploy Agent for Project 1 (Async Task Queue API - File Processing).

## YOUR TASK
Create all Docker and infrastructure files to run the complete stack locally.

## CONTEXT
Read these files:
- pyproject.toml — dependencies
- src/main.py — FastAPI app entrypoint
- src/infrastructure/celery_app.py — Celery app for worker commands
- src/infrastructure/config.py — environment variables needed
- docs/analysis/legacy-patterns.md — legacy docker-compose pattern

## STACK COMPONENTS

| Service | Image/Build | Ports | Purpose |
|---------|------------|-------|---------|
| redis | redis:7-alpine | 6379 | Broker (DB 0) + Results (DB 1) + Job Store (DB 2) |
| api | Build from Dockerfile | 8000 | FastAPI app (uvicorn) |
| worker_high | Build from Dockerfile | - | Celery worker: jobs_high queue, concurrency=4 |
| worker_low | Build from Dockerfile | - | Celery worker: jobs_low queue, concurrency=2 |
| flower | Build from Dockerfile | 5555 | Celery monitoring UI |

## WHAT TO CREATE

### 1. Dockerfile
- Base: python:3.11-slim
- Install system deps for Pillow and pdfplumber (libjpeg, libpng, poppler-utils)
- Copy pyproject.toml, install deps
- Copy src/ and client/
- No CMD (overridden by docker-compose)

### 2. docker-compose.yml
- All 5 services above
- Redis with healthcheck (redis-cli ping)
- api depends on redis (service_healthy)
- workers depend on redis (service_healthy)
- flower depends on redis
- Environment variables: TASKQUEUE_REDIS_URL, TASKQUEUE_REDIS_RESULT_BACKEND, TASKQUEUE_REDIS_JOB_STORE_URL
- Volume for redis_data persistence

### 3. .env.example
All TASKQUEUE_ variables with sensible defaults/placeholders.

### 4. .dockerignore
Exclude: .git, __pycache__, .venv, .env, .pytest_cache, base/, planner/, docs/, *.pyc

### 5. .gitignore
Standard Python + project-specific: .env, __pycache__, .venv, .pytest_cache, htmlcov/, *.egg-info, base/

### 6. Scripts
- scripts/start-api.sh: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
- scripts/start-worker-high.sh: celery -A src.infrastructure.celery_app worker
  --queues=jobs_high --concurrency=4 --loglevel=info --hostname=worker_high@%h
- scripts/start-worker-low.sh: celery -A src.infrastructure.celery_app worker
  --queues=jobs_low --concurrency=2 --loglevel=info --hostname=worker_low@%h

### 7. Makefile
Targets: up, down, logs, test, lint, shell, worker-logs, flower

## WRITE SCOPE
- Dockerfile, docker-compose.yml, .dockerignore, .env.example, .gitignore
- scripts/
- Makefile

## CRITICAL RULES
- NEVER write application code
- NO debug ports (no debugpy)
- NO certificate mounting
- NO references to CCEE, Lux, or proprietary systems
- Redis must have a healthcheck
- Workers must depend on Redis being healthy before starting
```

### Acceptance Criteria
- [ ] `docker-compose up` builds and starts all 5 services
- [ ] Redis healthcheck passes before workers start
- [ ] API accessible on port 8000
- [ ] Flower accessible on port 5555
- [ ] `make up`, `make down`, `make logs` work
- [ ] `.env.example` contains all required environment variables
- [ ] No CCEE/Lux references

---

## Stage 5 — QA Agent (Tests)

### Summary
| Field | Value |
|---|---|
| **Agent** | QA |
| **Window** | HYBRID (stays open if tests fail) |
| **Depends on** | Stages 2, 3, 4 |
| **Produces** | `tests/`, `docs/qa_reports/test-coverage-plan.md` |
| **Write scope** | `tests/`, `docs/qa_reports/` |

### Seed Prompt

```
You are the QA Agent for Project 1 (Async Task Queue API - File Processing).

## YOUR TASK
Write comprehensive tests that validate all contracts and integration points.
You NEVER modify source code.

## CONTEXT
Read ALL files in:
- src/domain/ — domain contracts
- src/application/ — use cases, DTOs, mappers
- src/adapters/ — API routes, Redis store, processors
- src/infrastructure/ — Celery, Redis, config, rate limiter
- client/ — multi-threaded client library
- docs/planning/api-contract.md — expected API behavior

## WHAT TO TEST

### Unit Tests

1. tests/unit/test_job_models.py
   - Job entity creation with valid data
   - Enum values (JobStatus, JobPriority, JobType)
   - DTO validation (invalid job_type, missing payload)

2. tests/unit/test_processors.py
   - Each processor: valid input -> correct output shape
   - Each processor: invalid base64 -> raises ProcessingError
   - Each processor: empty content -> raises ProcessingError
   - Processor registry maps all 4 JobTypes

3. tests/unit/test_rate_limiter.py
   - Allows requests under limit
   - Blocks requests at limit
   - Window slides (old entries expire)
   - Fail-open: returns True when Redis unavailable
   - reset clears counter

4. tests/unit/test_client.py (mock all HTTP)
   - submit_job: POST -> returns job_id
   - get_status: GET -> returns JobResult
   - submit_and_wait: polls until success
   - submit_async: returns Future, does not block
   - submit_batch: returns list of Futures
   - Timeout: raises JobTimeoutError
   - Failed job: raises JobFailedError
   - Exponential backoff: intervals increase (mock time.sleep)
   - shutdown: executor terminated
   - Context manager: shutdown called on exit

### Integration Tests (require Redis + Celery)

5. tests/integration/test_job_flow.py
   - Submit each job type -> poll -> success with correct result shape
   - Invalid payload -> job fails
   - Cancel pending job -> CANCELLED
   - Get non-existent job -> 404
   - Priority routing: high -> jobs_high, low -> jobs_low

6. tests/integration/test_batch_flow.py
   - Submit 4 different types via client.submit_batch()
   - All Futures resolve
   - BatchResult correct counts

### E2E Tests (require full docker-compose stack)

7. tests/e2e/test_api_contracts.py
   - POST /jobs returns 202 with correct schema
   - GET /jobs/{id} returns correct schema per status
   - DELETE /jobs/{id} returns confirmation
   - GET /jobs returns list
   - GET /health returns components
   - GET /queue/stats returns metrics
   - Rate limiting: burst -> 429 after limit

### Test Plan

8. docs/qa_reports/test-coverage-plan.md
   - All test files and coverage areas
   - Risk areas (threading, Redis failures, large files)

## WRITE SCOPE
- tests/
- docs/qa_reports/

## CRITICAL RULES
- NEVER modify source code in src/ or client/
- Use pytest fixtures extensively
- Mock Redis for unit tests, real Redis for integration
- Mock HTTP for client unit tests
- Use pytest.mark.integration and pytest.mark.e2e markers
- Generate sample files in-memory (small CSV, tiny PNG, simple PDF)
- Test threading with concurrent.futures.wait() and short timeouts
```

### Acceptance Criteria
- [ ] `pytest tests/unit/ -v` passes without external dependencies
- [ ] `pytest tests/integration/ -v -m integration` passes with Redis + Celery
- [ ] Client threading tests verify non-blocking behavior
- [ ] All 4 processors tested (positive + negative cases)
- [ ] Rate limiter fail-open tested
- [ ] Test coverage plan documented

---

## Stage 6 — Backend Agent (Demos + Examples)

### Summary
| Field | Value |
|---|---|
| **Agent** | Backend |
| **Window** | PERSISTENT |
| **Depends on** | Stages 2, 3, 4 |
| **Produces** | `examples/` |
| **Write scope** | `examples/` |

### Seed Prompt

```
You are the Backend Agent for Project 1. This is a DEDICATED STAGE for demo scripts.

## YOUR TASK
Create compelling demo scripts that showcase the multi-threaded client library.

## CONTEXT
Read:
- client/client.py — the client API
- client/models.py — JobResult, BatchResult
- docs/planning/api-contract.md — API contract

## WHAT TO CREATE

### 1. examples/demo_simple.py
Simplest possible usage — submit one job, wait, print result.

### 2. examples/demo_multithreaded.py (MAIN SHOWCASE)
Submit 3 jobs of different types, continue doing work on main thread,
collect results as they arrive using concurrent.futures.as_completed().
Print timing info showing main thread was never blocked.

### 3. examples/demo_batch.py
Submit 8 jobs in batch, show progress as Futures complete, print BatchResult summary.

### 4. examples/sample_files/
Small valid files for demos:
- sample.csv — 20-row CSV with name, amount, date columns
- sample.txt — 200-word text paragraph
- sample.png — small colored image
- sample.pdf — 1-page PDF with text

### 5. examples/README.md
Prerequisites, how to run each demo, expected output.

## WRITE SCOPE: examples/ only

## CRITICAL RULES
- Each demo includes base64 encoding step (show real workflow)
- Print output clearly shows threading (main thread free, async results)
- Handle errors gracefully
- Include timing information
```

### Acceptance Criteria
- [ ] All 3 demos run against live stack
- [ ] `demo_multithreaded.py` shows main thread doing work while results arrive
- [ ] Sample files are small but valid
- [ ] `examples/README.md` has clear instructions

---

## Stage 7 — Docs Agent (Documentation)

### Summary
| Field | Value |
|---|---|
| **Agent** | Docs |
| **Window** | EPHEMERAL |
| **Depends on** | Stages 2, 3, 4, 5, 6 |
| **Produces** | `README.md`, `docs/human/`, `docs/ai/` |
| **Write scope** | `docs/human/`, `docs/ai/`, `README.md` |

### Seed Prompt

```
You are the Docs Agent for Project 1 (Async Task Queue API - File Processing).

## YOUR TASK
Create comprehensive documentation for both human developers and AI agents.

## CONTEXT
Read ALL source code and existing docs to understand the full system.

## WHAT TO CREATE

### 1. README.md (top-level)
- Title + 1-line description
- Architecture diagram (Mermaid) — POST /jobs -> FastAPI -> Celery -> Processor -> Redis -> GET /jobs/{id}
- Client threading diagram (Mermaid) — main thread + ThreadPoolExecutor + polling threads
- Features (8-10 bullets)
- Quick Start (docker-compose up + curl examples)
- API Reference table
- Client Library section (simple, async, batch examples)
- Tech stack table
- Project structure tree
- Testing instructions

### 2. docs/human/architecture.md
- Hexagonal architecture explanation
- Layer responsibilities
- Redis usage (3 DBs: broker, results, job store)
- Queue routing, retry strategy, rate limiting algorithm

### 3. docs/human/client-library.md
- Design philosophy (non-blocking, Future-based)
- Threading model with diagram
- Full TaskQueueClient API reference
- Error handling, performance tuning, thread safety

### 4. docs/human/api-reference.md
Every endpoint with method, path, request/response schemas, error responses, rate limiting.

### 5. docs/ai/CLAUDE.md
AI agent context: project purpose, architecture, key files, conventions, constraints.

### 6. docs/ai/agent-handoff.md
Continuation guide: current state, known limitations, future enhancements.

## WRITE SCOPE: docs/human/, docs/ai/, README.md

## CRITICAL RULES
- README must include TWO Mermaid diagrams (server + client threading)
- NO references to CCEE, Lux, or proprietary systems
- Client library section in README is TOP priority
- All diagrams must be valid Mermaid syntax
- API examples use realistic payloads
```

### Acceptance Criteria
- [ ] `README.md` renders on GitHub with Mermaid diagrams
- [ ] Client library has dedicated doc page
- [ ] `docs/ai/CLAUDE.md` enables AI agents to understand project in one read
- [ ] No CCEE/Lux references
- [ ] API reference covers all 6 endpoints with examples

---

## Stage 8 — QA Agent (Final Validation)

### Summary
| Field | Value |
|---|---|
| **Agent** | QA |
| **Window** | HYBRID |
| **Depends on** | All previous stages |
| **Produces** | `docs/qa_reports/final-validation.md` |
| **Write scope** | `docs/qa_reports/` |

### Seed Prompt

```
You are the QA Agent performing FINAL VALIDATION for Project 1.

## YOUR TASK
Run all tests, verify documentation, check for security issues, and produce a final report.

## CHECKLIST

### Code Quality
- [ ] All files have docstrings
- [ ] No circular imports
- [ ] No hardcoded secrets
- [ ] .env is in .gitignore
- [ ] No CCEE/Lux/proprietary references anywhere

### Tests
- [ ] pytest tests/unit/ passes
- [ ] pytest tests/integration/ passes (with Redis)
- [ ] Client threading tests pass
- [ ] Rate limiter fail-open tested

### Documentation
- [ ] README.md Mermaid diagrams render
- [ ] API examples match actual response shapes
- [ ] Client library examples work

### Security
- [ ] No secrets in committed files
- [ ] .env.example has only placeholders
- [ ] No real file paths or internal URLs

### Docker
- [ ] docker-compose up builds successfully
- [ ] All services start and healthchecks pass
- [ ] API responds on port 8000
- [ ] Flower responds on port 5555

## OUTPUT
Write docs/qa_reports/final-validation.md with:
- Pass/fail for each checklist item
- Bug list (if any) with severity
- Recommendation: SHIP or BLOCK with reasons

## WRITE SCOPE: docs/qa_reports/ only
```

### Acceptance Criteria
- [ ] Report covers every checklist item
- [ ] Bugs documented with reproduction steps
- [ ] Final recommendation provided (SHIP or BLOCK)

---

## Stage 9 — Process Agent (Retrospective)

### Summary
| Field | Value |
|---|---|
| **Agent** | Process |
| **Window** | EPHEMERAL |
| **Depends on** | All previous stages |
| **Produces** | `docs/qa_reports/retrospective.md` |
| **Write scope** | `docs/qa_reports/` |

### Seed Prompt

```
You are the Process Agent for Project 1 (Async Task Queue API - File Processing).

## YOUR TASK
Produce a retrospective analyzing the agent pipeline execution for this project.

## WHAT TO ANALYZE
1. How well did the agent stages map to this project's needs?
2. What adaptations were needed vs the standard Project 4 pipeline?
3. Which stages had the cleanest handoffs? Which were problematic?
4. Was the Redis-only (no SQL) adaptation smooth?
5. Did the separate Client Library stage work well?
6. Time spent per stage (estimate from git history)

## OUTPUT
Write docs/qa_reports/retrospective.md with:
- What went well (keep doing)
- What was awkward (adapt for future projects)
- Pipeline improvement recommendations
- Lessons for non-SQL hexagonal projects

## WRITE SCOPE: docs/qa_reports/ only
```

### Acceptance Criteria
- [ ] Retrospective is actionable (specific recommendations)
- [ ] Covers pipeline-level and project-level observations
- [ ] Identifies lessons for future non-SQL projects

---

## Key Legacy Files to Adapt

| Legacy File | New Target |
|---|---|
| `base/api_ccee/central_api/infrastructure/task_queue/celery_app.py` | `src/infrastructure/celery_app.py` |
| `base/api_ccee/central_api/infrastructure/task_queue/rate_limiter.py` | `src/infrastructure/rate_limiter.py` |
| `base/api_ccee/central_api/infrastructure/task_queue/tasks.py` | `src/infrastructure/celery_tasks.py` |
| `base/api_ccee/central_api/core/models/queue_models.py` | `src/domain/` + `src/application/dtos/` |
| `base/api_ccee/central_api/web/queue/monitoring.py` | `src/adapters/inbound/api/monitoring_router.py` |
| `base/api_ccee/central_api/web/queue/queue_management.py` | `src/adapters/inbound/api/jobs_router.py` |
| `base/api_ccee/ccee_queue_client/client.py` | `client/client.py` (+ threading) |
| `base/api_ccee/docker-compose.yml` | `docker-compose.yml` |

---

## Verification Checkpoints

| After Stage | Verification |
|---|---|
| Stage 2 | `docker-compose up redis` + run API locally, `curl POST /jobs` returns 202 |
| Stage 4 | `docker-compose up` → all 5 services healthy |
| Stage 5 | `pytest tests/unit/` all green |
| Stage 6 | Run demo scripts, verify threading output |
| Stage 8 | Final validation report says SHIP |
