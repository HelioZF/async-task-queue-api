# Project 1 — Async Task Queue API
## Implementation Plan

> **Portfolio goal:** Showcase production-grade async architecture (FastAPI + Celery + Redis) with a **multi-threaded Python client** that demonstrates both server-side and client-side async patterns — in a clean, generic domain without any proprietary code or business references.

---

## 1. New Domain: File Processing Service

### What it does
A REST API where clients submit **file processing jobs** and get results asynchronously.
- Upload a file → receive a `job_id`
- Poll `GET /jobs/{job_id}` → check status and retrieve result when done
- Jobs run in the background (Celery workers), prioritized by urgency

### Example Job Types
| Job Type | Input | Output |
|---|---|---|
| `csv_summary` | CSV file | Row count, column stats, preview |
| `word_count` | Text / TXT file | Word frequency analysis |
| `image_resize` | Image (PNG/JPG) | Resized image (base64 or URL) |
| `pdf_extract` | PDF file | Extracted plain text |

> **Why this domain?** File processing is universally understood, requires no business context, and naturally justifies async queuing (heavy processing shouldn't block HTTP responses).

---

## 2. What to Keep from the Base Project

| Pattern | Source Location | Keep As-Is? | Action |
|---|---|---|---|
| Hexagonal architecture layout | `central_api/core`, `infrastructure`, `web` | ✅ Yes | Rename folders, keep structure |
| Celery + Redis setup | `infrastructure/task_queue/celery_app.py` | ✅ Yes | Keep, remove CCEE-specific config |
| Priority queue routing (high/low) | `tasks.py`, `queue_config.py` | ✅ Yes | Keep exactly, rename queues |
| Rate limiter (sliding window, Redis) | `infrastructure/task_queue/rate_limiter.py` | ✅ Yes | Keep, generalize resource name |
| Retry logic (exponential backoff + jitter) | `tasks.py` decorators | ✅ Yes | Keep exactly |
| Task models (TaskStatus, TaskPriority, etc.) | `core/models/queue_models.py` | ✅ Yes | Keep, rename to `job_models.py` |
| `TaskResponse` / `TaskStatusResponse` | `core/models/queue_models.py` | ✅ Yes | Rename to `JobResponse` / `JobStatusResponse` |
| Health check endpoint | `web/queue/monitoring.py` | ✅ Yes | Keep, clean up CCEE references |
| Flower monitoring | `docker-compose.yml` | ✅ Yes | Keep |
| Fail-open for rate limiter | `rate_limiter.py` | ✅ Yes | Keep |
| `.env.example` pattern | `.env` / `config.py` | ✅ Yes | Clean up secrets |
| SOAP client | `infrastructure/soap_client/` | ❌ No | Remove entirely |
| mTLS / WS-Security | `infrastructure/httpx_client/gateway.py` | ❌ No | Remove entirely |
| CCEE domain models | `core/models/obligations.py`, `common.py` | ❌ No | Replace with file job models |
| Auto-pagination logic | `tasks.py` | ❌ No | Remove (not needed) |
| `ccee_queue_client` package | `ccee_queue_client/` | 🔄 Adapt | Rebuild as `task_queue_client` |

---

## 3. New Project Folder Structure

```
async-task-queue-api/
├── app/
│   ├── main.py                     # FastAPI app, register routers
│   ├── config.py                   # Pydantic Settings (env vars)
│   ├── core/
│   │   ├── models/
│   │   │   ├── job_models.py       # JobStatus, JobPriority, JobResponse, etc.
│   │   │   └── errors.py           # Custom exception types
│   │   ├── contracts/
│   │   │   └── processors.py       # IFileProcessor interface (port)
│   │   └── queue_config.py         # Queue names, rate limits, timeouts
│   ├── infrastructure/
│   │   ├── task_queue/
│   │   │   ├── celery_app.py       # Celery configuration
│   │   │   ├── tasks.py            # Celery task definitions (one per job type)
│   │   │   └── rate_limiter.py     # Sliding window rate limiter (Redis)
│   │   └── processors/
│   │       ├── csv_processor.py    # CSV summary logic
│   │       ├── text_processor.py   # Word count logic
│   │       ├── image_processor.py  # Image resize logic
│   │       └── pdf_processor.py    # PDF text extraction logic
│   └── web/
│       ├── jobs/
│       │   ├── submit.py           # POST /jobs — submit a new job
│       │   └── status.py           # GET /jobs/{id}, DELETE /jobs/{id}
│       └── monitoring/
│           └── health.py           # GET /health, GET /queue/stats
├── client/                         # Multi-threaded client library
│   ├── __init__.py
│   ├── client.py                   # TaskQueueClient — sync + async (threaded) API
│   ├── poller.py                   # _JobPoller — background polling via ThreadPoolExecutor
│   ├── models.py                   # JobResult, BatchResult dataclasses
│   └── exceptions.py              # JobTimeoutError, JobFailedError, etc.
├── examples/
│   └── demo_multithreaded.py       # End-to-end demo: submit jobs, do work, collect results
├── tests/
│   ├── unit/
│   │   ├── test_rate_limiter.py
│   │   └── test_job_models.py
│   ├── integration/
│   │   └── test_job_flow.py        # Submit → poll → result full flow
│   └── conftest.py
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── README.md
```

---

## 4. Tech Stack

| Component | Technology | Version |
|---|---|---|
| Web Framework | FastAPI | ^0.115 |
| ASGI Server | Uvicorn | ^0.30 |
| Task Queue | Celery | ^5.4 |
| Message Broker | Redis | 7-alpine (Docker) |
| Result Backend | Redis (separate DB) | — |
| Data Validation | Pydantic v2 | ^2.7 |
| Settings | pydantic-settings | ^2.3 |
| Logging | Loguru | ^0.7 |
| Queue Monitoring | Flower | ^2.0 |
| File Processing | pandas, Pillow, pdfplumber | latest |
| Client Threading | concurrent.futures (stdlib) | — |
| Client HTTP | requests | ^2.31 |
| Testing | pytest, pytest-asyncio, httpx | latest |
| Containerization | Docker + docker-compose | — |
| Python | 3.11 | — |

---

## 5. API Design

### Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/jobs` | Submit a new job. Returns `job_id` immediately. |
| `GET` | `/jobs/{job_id}` | Poll job status and retrieve result when done. |
| `DELETE` | `/jobs/{job_id}` | Cancel a pending or running job. |
| `GET` | `/jobs` | List recent jobs (optional, good for demo). |
| `GET` | `/health` | Basic health check (Redis, workers). |
| `GET` | `/queue/stats` | Detailed worker and queue statistics. |
| `GET` | `/docs` | Swagger UI (FastAPI auto-generated). |

### `POST /jobs` Request Body

```json
{
  "job_type": "csv_summary",
  "priority": "high",
  "payload": {
    "file_content": "<base64-encoded file content>",
    "filename": "sales_data.csv"
  }
}
```

### `POST /jobs` Response (202 Accepted)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "priority": "high",
  "message": "Job submitted successfully",
  "check_status_url": "/jobs/550e8400-e29b-41d4-a716-446655440000",
  "estimated_time": "5–15 seconds"
}
```

### `GET /jobs/{job_id}` Response — Success

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "job_type": "csv_summary",
  "result": {
    "row_count": 1500,
    "columns": ["name", "amount", "date"],
    "preview": [...]
  },
  "created_at": "2025-06-01T10:00:00Z",
  "completed_at": "2025-06-01T10:00:07Z"
}
```

### `GET /jobs/{job_id}` Response — Pending

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "job_type": "csv_summary",
  "result": null,
  "created_at": "2025-06-01T10:00:00Z",
  "completed_at": null
}
```

---

## 6. Key Models

```python
# app/core/models/job_models.py

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobPriority(str, Enum):
    LOW = "low"      # Processed in background, 1–5 min
    HIGH = "high"    # Processed ASAP, 5–15 sec

class JobType(str, Enum):
    CSV_SUMMARY = "csv_summary"
    WORD_COUNT = "word_count"
    IMAGE_RESIZE = "image_resize"
    PDF_EXTRACT = "pdf_extract"

class JobRequest(BaseModel):
    job_type: JobType
    priority: JobPriority = JobPriority.LOW
    payload: Dict[str, Any]

class JobResponse(BaseModel):        # Immediate response after POST /jobs
    job_id: str
    status: str
    priority: str
    message: str
    check_status_url: str
    estimated_time: str

class JobStatusResponse(BaseModel):  # Response for GET /jobs/{id}
    job_id: str
    status: JobStatus
    job_type: Optional[JobType]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    created_at: Optional[datetime]
    completed_at: Optional[datetime]
```

---

## 7. Queue Architecture

```
POST /jobs
    │
    ▼
FastAPI Router
    │
    ├── Generate UUID job_id
    ├── Determine queue (high or low priority)
    └── celery_task.apply_async(queue=..., kwargs={job_type, payload})
         │
         ▼
    Return JobResponse (202) with job_id

         [Background]
              │
              ▼
    Celery Worker picks up task
         │
         ├── Dispatch to correct processor:
         │       csv_summary   → CsvProcessor.process()
         │       word_count    → TextProcessor.process()
         │       image_resize  → ImageProcessor.process()
         │       pdf_extract   → PdfProcessor.process()
         │
         ├── On success → Store result in Redis (TTL: 1h)
         └── On failure → Retry (max 3x, exponential backoff)
                           → After max retries: store error in Redis
```

### Queues

| Queue | Workers | Concurrency | Use |
|---|---|---|---|
| `jobs_high` | `worker_high` | 4 | High-priority jobs |
| `jobs_low` | `worker_low` | 2 | Low-priority/background jobs |

---

## 8. Client Architecture — Multi-Threaded Polling

### Design Philosophy

In production, a client should **never block its main thread** waiting for a job to complete. Our client library offers two modes:

1. **Synchronous** — `submit_and_wait()` for simple scripts (blocks until done)
2. **Async (threaded)** — `submit_async()` returns a `Future`, polling happens in a background thread

The threaded mode is the star of the show — it demonstrates real-world patterns where the caller continues doing work while results arrive in the background.

### Thread Lifecycle

```
Main Thread                         ThreadPoolExecutor (polling threads)
──────────                          ────────────────────────────────────
client = TaskQueueClient(url)
                                    [pool created with max_workers=N]
future = client.submit_async(
    job_type, payload, priority
)
  ├── POST /jobs → job_id
  ├── executor.submit(_poll_job)  ──►  _poll_job(job_id) starts
  └── return Future                       │
                                          ├── GET /jobs/{id} → pending
 # Main thread continues working          ├── sleep(poll_interval)
do_other_work()                           ├── GET /jobs/{id} → processing
do_more_work()                            ├── sleep(poll_interval)
                                          ├── GET /jobs/{id} → success ✓
                                          └── return JobResult
result = future.result()  ◄────────── Future resolves
process(result)
```

### Batch Mode — Multiple Jobs in Parallel

```
futures = client.submit_batch([
    ("csv_summary",   payload1, "high"),
    ("image_resize",  payload2, "low"),
    ("pdf_extract",   payload3, "high"),
])

# Each job gets its own polling thread from the pool
# Main thread is free immediately

for future in as_completed(futures):
    result = future.result()    # Results arrive as they complete
    print(f"{result.job_id}: {result.status}")
```

### Key Design Decisions

| Decision | Choice | Why |
|---|---|---|
| Threading library | `concurrent.futures.ThreadPoolExecutor` | Stdlib, clean `Future` API, no extra dependencies |
| Pool size | Configurable, default `max_workers=4` | Matches typical batch sizes without overloading |
| Poll strategy | Exponential backoff (0.5s → 1s → 2s → 5s cap) | Avoids hammering the API, adapts to job duration |
| Timeout | Per-job configurable, default 120s | Prevents zombie threads on stuck jobs |
| Error handling | `Future` propagates exceptions to `.result()` | `JobTimeoutError`, `JobFailedError` raised on main thread |
| Thread safety | `requests.Session` per thread (thread-local) | Avoids connection sharing issues |
| Cleanup | `client.shutdown()` or context manager (`with`) | Ensures executor is properly terminated |

### Client API Surface

```python
class TaskQueueClient:
    def __init__(self, base_url: str, max_workers: int = 4,
                 default_timeout: float = 120, poll_interval: float = 0.5,
                 max_poll_interval: float = 5.0):
        ...

    # ── Synchronous (blocking) ──
    def submit_job(self, job_type, payload, priority="low") -> str:
        """Submit a job, return job_id immediately."""

    def get_status(self, job_id: str) -> JobResult:
        """Single poll — check current status."""

    def submit_and_wait(self, job_type, payload, priority="low",
                        timeout=120) -> JobResult:
        """Submit + block until result (simple mode)."""

    # ── Async / Multi-threaded (non-blocking) ──
    def submit_async(self, job_type, payload, priority="low",
                     timeout=120) -> Future[JobResult]:
        """Submit job, return Future. Polling runs in background thread."""

    def submit_batch(self, jobs: list[tuple]) -> list[Future[JobResult]]:
        """Submit multiple jobs, each polled in its own thread."""

    # ── Lifecycle ──
    def shutdown(self, wait=True):
        """Shut down the thread pool."""

    def __enter__(self) / __exit__():
        """Context manager support."""
```

### Client Models

```python
@dataclass
class JobResult:
    job_id: str
    status: str             # "success", "failed", "cancelled"
    job_type: str
    result: dict | None     # Processor output (on success)
    error: str | None       # Error message (on failure)
    created_at: datetime
    completed_at: datetime
    elapsed: float          # Total seconds from submit to result

@dataclass
class BatchResult:
    total: int
    succeeded: int
    failed: int
    results: list[JobResult]
```

---

## 9. Implementation Phases

### Phase 1 — Skeleton & Infrastructure
- [ ] Set up `pyproject.toml` with all dependencies
- [ ] Create folder structure (see Section 3)
- [ ] Implement `config.py` (Pydantic Settings, `.env.example`)
- [ ] Implement `core/models/job_models.py`
- [ ] Implement `core/models/errors.py`
- [ ] Configure `infrastructure/task_queue/celery_app.py` (adapted from base)
- [ ] Set up `docker-compose.yml` (Redis, API, 2 workers, Flower)
- [ ] Set up `Dockerfile`
- [ ] Basic `app/main.py` with health check endpoint
- [ ] Draft Mermaid architecture diagram (server flow + client threading lifecycle) — finalize copy in README at Phase 7
- **Checkpoint:** `docker-compose up` starts all services, `/health` returns 200

### Phase 2 — Job Submission & Polling
- [ ] Implement `core/queue_config.py`
- [ ] Implement `web/jobs/submit.py` (POST /jobs)
- [ ] Implement `web/jobs/status.py` (GET /jobs/{id}, DELETE /jobs/{id})
- [ ] Implement `infrastructure/task_queue/tasks.py` (generic job dispatcher)
- [ ] Implement `infrastructure/task_queue/rate_limiter.py` (adapted from base)
- [ ] Write unit tests for `JobRequest` / `JobResponse` model validation (`test_job_models.py`) — invalid types, missing fields, enum boundaries
- **Checkpoint:** Submit a job, poll for it, see it go pending → processing → success (even with a stub processor)

### Phase 3 — File Processors
- [ ] Implement `infrastructure/processors/csv_processor.py`
- [ ] Implement `infrastructure/processors/text_processor.py`
- [ ] Implement `infrastructure/processors/image_processor.py`
- [ ] Implement `infrastructure/processors/pdf_processor.py`
- [ ] Connect processors to task dispatcher via `IFileProcessor` interface
- [ ] Write unit tests for each processor — mock file I/O, assert output schema matches `JobStatusResponse.result` shape
- **Checkpoint:** All 4 job types return correct results end-to-end

### Phase 4 — Monitoring & Observability
- [ ] Implement `web/monitoring/health.py` (Redis ping, worker check, queue depth)
- [ ] Implement `GET /queue/stats` (queue sizes, worker count, processed jobs)
- [ ] Structured logging with Loguru (job_id in every log line)
- [ ] Write unit tests for `rate_limiter.py` — sliding window behavior, fail-open scenario (`test_rate_limiter.py`)
- **Checkpoint:** Flower UI running at `:5555`, `/queue/stats` returns live metrics

### Phase 5 — Multi-Threaded Client Library
- [ ] Implement `client/exceptions.py` (`JobTimeoutError`, `JobFailedError`, `ApiConnectionError`)
- [ ] Implement `client/models.py` (`JobResult`, `BatchResult` dataclasses)
- [ ] Implement `client/poller.py` (`_JobPoller` — encapsulates poll loop with exponential backoff)
- [ ] Implement `client/client.py` (`TaskQueueClient` class):
  - Sync API: `submit_job()`, `get_status()`, `submit_and_wait()`
  - Threaded API: `submit_async()` → returns `Future[JobResult]`
  - Batch API: `submit_batch()` → returns `list[Future[JobResult]]`
  - Lifecycle: `shutdown()`, context manager (`with` statement)
- [ ] Thread pool via `concurrent.futures.ThreadPoolExecutor`
- [ ] Exponential backoff polling (0.5s → 1s → 2s → 5s cap)
- [ ] Thread-safe HTTP sessions (`requests.Session` per thread)
- **Checkpoint:** `submit_async()` returns a `Future`, main thread stays unblocked, result arrives via `.result()`

### Phase 6 — Demo & Examples
- [ ] Implement `examples/demo_multithreaded.py`:
  - Submit 3+ jobs of different types
  - Show main thread doing other work while polling runs
  - Collect results via `as_completed(futures)`
  - Print job results with elapsed time
- [ ] Implement `examples/demo_batch.py`:
  - Submit a batch of 5-10 jobs
  - Show `BatchResult` summary (succeeded/failed counts)
- **Checkpoint:** Running the demo against a live API shows the full multi-threaded lifecycle

### Phase 7 — Tests & Documentation
- [ ] Unit tests: `test_rate_limiter.py`, `test_job_models.py`
- [ ] Unit tests: `test_client.py` (mock HTTP, verify threading behavior, test timeout/error paths)
- [ ] Integration test: full job lifecycle (submit → poll → result) via both sync and threaded client
- [ ] Write `README.md` with architecture diagram (Mermaid), setup guide, example requests
- [ ] Add **Client Library** section to README with multi-threaded usage examples
- [ ] Clean `.gitignore` (no secrets, no `.env`, no `__pycache__`)
- **Checkpoint:** `pytest` passes, README is clear and complete

---

## 10. README Structure (to write at the end)

```markdown
# Async Task Queue API

> A production-ready background job processing service built with FastAPI, Celery, and Redis — with a multi-threaded Python client library.

## Architecture
[Mermaid diagram — server side + client threading diagram]

## Features
- Async job submission with immediate job_id
- Priority queues (high/low)
- Automatic retry with exponential backoff
- Rate limiting (sliding window, Redis-backed)
- Real-time monitoring (Flower)
- **Multi-threaded client library** with Future-based API
- Background polling with exponential backoff
- Batch job submission with parallel result collection

## Quick Start
docker-compose up

## API Reference
[Table of endpoints]

## Client Library Usage
### Simple (blocking)
[submit_and_wait example]

### Multi-threaded (non-blocking)
[submit_async + Future example]

### Batch mode
[submit_batch + as_completed example]
```

---

## 11. Sensitive Information Checklist

Before pushing to GitHub, verify:
- [ ] No references to "CCEE", "Lux", "Lux Energia", or any company name
- [ ] No real credentials in any file (check `.env`, `config.py`, test files)
- [ ] No real certificates or private keys (`cert/` folder must not exist)
- [ ] No internal URLs or IP addresses
- [ ] No references to internal system names (obligations, measurements, ERCAP, etc.)
- [ ] `.env` is in `.gitignore`
- [ ] `.env.example` has only placeholder values (e.g., `REDIS_URL=redis://localhost:6379/0`)
