# Legacy Pattern Extraction Report

> **Stage 0 — Code Analyst Agent**
> Extracted reusable architectural patterns from the legacy codebase.
> All proprietary references have been stripped.

---

## Pattern 1: Celery Application Configuration

**Source:** `infrastructure/task_queue/celery_app.py`

**Pattern:** Centralized Celery app factory with configuration-driven settings, priority queue routing, and auto-discovery.

```python
celery_app = Celery(
    "app_name",
    broker=config.celery_broker_url,
    backend=config.celery_result_backend
)

celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='America/Sao_Paulo',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=config.worker_prefetch_multiplier,
    worker_max_tasks_per_child=config.worker_max_tasks_per_child,
    result_expires=config.celery_task_result_expires,
    task_soft_time_limit=config.task_soft_time_limit,
    task_time_limit=config.task_time_limit,
    task_routes={
        'module.tasks.task_name': {'queue': config.queue_name}
    },
)

celery_app.autodiscover_tasks(['module.infrastructure'])
```

**Key design decisions:**
- `task_acks_late=True` — requeue tasks if worker crashes mid-execution
- `task_track_started=True` — enables STARTED state for polling
- `worker_prefetch_multiplier=1` — one task at a time per worker (prevents starvation)
- `worker_max_tasks_per_child=100` — prevents memory leaks by recycling workers

**Adaptation notes:**
- Rename app from legacy name to `"file_processing_api"`
- Consolidate 4 queues (soap_high/low, httpx_high/low) into 2 (`jobs_high`, `jobs_low`)
- Remove `result_backend_transport_options` (Sentinel-specific config not needed)
- Change timezone to UTC for generic use

**Target file:** `src/infrastructure/celery_app.py`

---

## Pattern 2: Sliding Window Rate Limiter (Fail-Open)

**Source:** `infrastructure/task_queue/rate_limiter.py`

**Pattern:** Redis sorted set-based sliding window rate limiter with atomic operations via pipeline. Critically uses fail-open design — allows requests when Redis is unavailable.

```python
class RateLimiter:
    def __init__(self, redis_url=None, key_prefix="rate_limit"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.prefix = key_prefix

    def is_allowed(self, resource: str, max_requests: int, window: int = 60) -> bool:
        key = f"{self.prefix}:{resource}"
        current_time = int(time())
        try:
            pipe = self.redis.pipeline()
            pipe.zadd(key, {str(current_time): current_time})     # Add current timestamp
            pipe.zremrangebyscore(key, 0, current_time - window)   # Remove expired
            pipe.zcard(key)                                        # Count in window
            pipe.expire(key, window + 10)                          # Auto-cleanup
            results = pipe.execute()
            return results[2] <= max_requests
        except redis.RedisError:
            return True  # FAIL-OPEN: allow request if Redis is down

    def get_current_count(self, resource: str, window: int = 60) -> int:
        # Cleanup + count

    def reset(self, resource: str):
        # Delete key
```

**Key design decisions:**
- **Sorted set** with timestamps as both member and score — enables efficient range queries
- **Pipeline** for atomicity — all 4 operations execute in a single round-trip
- **Fail-open** — production-critical: never block requests due to infrastructure failure
- **Auto-expire** with `window + 10` seconds — garbage collection safety net
- **Global singleton** instance for shared state across the app

**Adaptation notes:**
- This pattern is 100% generic — reusable as-is
- Only change: resource names from legacy-specific to `"file_processing"` or per-job-type limiting
- Consider accepting Redis client via dependency injection instead of global singleton

**Target file:** `src/infrastructure/rate_limiter.py`

---

## Pattern 3: Celery Task with Retry Logic (Exponential Backoff + Jitter)

**Source:** `infrastructure/task_queue/tasks.py`

**Pattern:** Celery task decorator with built-in retry configuration, rate limit checking, and structured error responses.

```python
class RateLimitedTask(Task):
    """Base task class with rate limiting hook."""
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)

@celery_app.task(
    bind=True,
    base=RateLimitedTask,
    max_retries=3,
    autoretry_for=(ConnectionError, Timeout),
    retry_backoff=True,
    retry_backoff_max=600,   # Max 10 min backoff
    retry_jitter=True        # Random jitter to prevent thundering herd
)
def execute_request(self, endpoint, params, method_name):
    # 1. Check rate limit
    if not rate_limiter.is_allowed("resource", max_requests=60, window=60):
        raise self.retry(countdown=5, max_retries=10)

    # 2. Execute operation
    result = do_work(params)

    # 3. Return structured response
    return {"success": True, "data": result, "endpoint": endpoint}

    # Error handling: structured JSON error details
    except SomeHTTPError as e:
        if e.status_code in [500, 502, 503, 504]:
            raise self.retry(exc=e, countdown=60)  # Retry on transient errors
        raise Exception(json.dumps(error_detail))   # Fail permanently on others
```

**Key design decisions:**
- `bind=True` — gives access to `self` for manual retry control
- `retry_backoff=True` + `retry_jitter=True` — exponential backoff with jitter prevents thundering herd
- `retry_backoff_max=600` — caps backoff at 10 minutes
- **Dual retry strategy**: automatic (`autoretry_for`) for connection errors, manual (`self.retry`) for rate limits and transient HTTP errors
- **Structured error JSON** — errors serialized as JSON strings for consistent parsing by status endpoint

**Adaptation notes:**
- Replace two task functions (soap/httpx) with single generic `process_job` dispatcher
- Remove SOAP/httpx-specific gateway calls, replace with processor registry dispatch
- Remove auto-pagination logic (not needed for file processing)
- Keep the `RateLimitedTask` base class pattern
- Keep dual retry strategy (auto for connection, manual for rate limits)

**Target file:** `src/infrastructure/celery_tasks.py`

---

## Pattern 4: Priority Queue Routing

**Source:** `core/queue_config.py` + `celery_app.py`

**Pattern:** Configuration-driven queue routing with two priority tiers per service type, allowing callers to choose urgency at submission time.

```python
class QueueConfig(BaseSettings):
    queue_high: str = "service_high"
    queue_low: str = "service_low"
    rate_limit: int = 60
    task_soft_time_limit: int = 300  # 5 min
    task_time_limit: int = 360       # 6 min

# At submission time:
task.apply_async(
    args=[...],
    queue=config.queue_high if priority == "high" else config.queue_low
)
```

**Key design decisions:**
- **Dedicated workers per queue** — high-priority workers don't get blocked by low-priority batch jobs
- **Soft + hard time limits** — soft limit raises `SoftTimeLimitExceeded` (task can cleanup), hard limit kills the task
- **Config via Pydantic Settings** — all values overridable via environment variables

**Adaptation notes:**
- Consolidate from 4 queues (soap_high/low + httpx_high/low) to 2 (`jobs_high`, `jobs_low`)
- Change env prefix from `QUEUE_` to `TASKQUEUE_`
- Add Redis DB 2 for job metadata store (legacy only uses DB 0 and 1)

**Target file:** `src/infrastructure/config.py`

---

## Pattern 5: Pydantic Models for Task Lifecycle

**Source:** `core/models/queue_models.py`

**Pattern:** Enum-based status tracking with separate request/response models for API contract clarity.

```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"

class TaskPriority(str, Enum):
    LOW = "low"
    HIGH = "high"

class TaskSubmitRequest(BaseModel):
    endpoint: str
    params: Dict[str, Any]
    priority: TaskPriority = TaskPriority.LOW

class TaskResponse(BaseModel):       # Submit response (202)
    task_id: str
    status: str
    priority: str
    message: str
    check_status_url: str
    estimated_time: str

class TaskStatusResponse(BaseModel):  # Poll response (200)
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: Optional[int] = None
```

**Key design decisions:**
- `str, Enum` — JSON-serializable enums that work seamlessly with Pydantic and Celery's JSON serializer
- Separate `TaskResponse` (submit) vs `TaskStatusResponse` (poll) — different data at different lifecycle stages
- `check_status_url` in submit response — self-documenting API (HATEOAS-lite)

**Adaptation notes:**
- Rename: TaskStatus → JobStatus, TaskPriority → JobPriority
- Add `JobType(str, Enum)` for file processing types (csv_summary, word_count, image_resize, pdf_extract)
- Add `CANCELLED` status (legacy only has RETRY, new project needs explicit cancellation)
- Split into domain entities (dataclass) and DTOs (Pydantic) per hexagonal architecture
- Move `endpoint` → `job_type`, `params` → `payload`

**Target file:** `src/domain/value_objects/enums.py` + `src/application/dtos/job_dtos.py`

---

## Pattern 6: Health Check + Monitoring Endpoints

**Source:** `web/queue/monitoring.py`

**Pattern:** Multi-component health check with granular status per dependency, plus detailed queue statistics endpoint.

```python
@router.get("/health")
async def queue_health():
    health_status = {"redis": "unknown", "workers": "unknown", "queues": "unknown"}

    # Check Redis via ping
    try:
        r = redis.from_url(config.redis_url)
        r.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"

    # Check workers via Celery inspect
    inspect = celery_app.control.inspect()
    stats = inspect.stats()
    health_status["workers"] = f"healthy ({len(stats)} workers)" if stats else "unhealthy"

    # Aggregate
    is_healthy = all("healthy" in str(s).lower() for s in health_status.values())
    return {"status": "healthy" if is_healthy else "unhealthy", "components": health_status}

@router.get("/stats")
async def queue_stats():
    # Workers: stats, active, scheduled, reserved
    # Queue depths: redis.llen(queue_name) for each queue
    # Rate limiting: current count vs limit for each resource
```

**Key design decisions:**
- **Component-level health** — not just "up/down" but per-component status
- **Queue depths via Redis `llen`** — direct measurement of backlog per priority
- **Rate limit stats included** — visibility into current consumption vs limits
- **Graceful error handling** — each check is independent, one failure doesn't prevent others

**Adaptation notes:**
- Update queue names to `jobs_high`/`jobs_low`
- Update rate limit resource names
- Remove SOAP/httpx-specific resource checks
- Keep the pattern of independent checks per component

**Target file:** `src/adapters/inbound/api/monitoring_router.py`

---

## Pattern 7: Task Status Polling + Cancellation

**Source:** `web/queue/queue_management.py`

**Pattern:** Celery `AsyncResult` for status polling with structured error extraction, plus task cancellation via `revoke`.

```python
@router.get("/{task_id}")
async def get_task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)

    response = {"task_id": task_id, "status": result.state}

    if result.state == "SUCCESS":
        response["result"] = result.result
        response["completed_at"] = result.date_done
    elif result.state == "FAILURE":
        # Parse structured JSON error from task
        error_info = result.info
        try:
            error_detail = json.loads(str(error_info))
        except:
            error_detail = {"message": str(error_info)}
        response["error"] = error_detail

    return response

@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    if result.state in ["PENDING", "STARTED", "RETRY"]:
        celery_app.control.revoke(task_id, terminate=True)
        return {"task_id": task_id, "message": "Cancelled", "previous_state": result.state}
```

**Key design decisions:**
- **AsyncResult** as the single source of truth for task state
- **JSON error parsing** — tasks serialize errors as JSON, status endpoint deserializes them
- **State-aware cancellation** — only cancels tasks in cancellable states
- `terminate=True` — sends SIGTERM to running tasks (not just removes from queue)

**Adaptation notes:**
- Rename `/tasks/` prefix to `/jobs/`
- Add `list_recent()` endpoint (legacy doesn't have job listing from a persistent store)
- The new project stores job metadata in Redis (DB 2), not just Celery result backend
- Status endpoint should read from RedisJobStore first, fall back to AsyncResult

**Target file:** `src/adapters/inbound/api/jobs_router.py`

---

## Pattern 8: Docker Compose Orchestration

**Source:** `docker-compose.yml`

**Pattern:** Multi-service stack with health-checked Redis, separate workers per queue, Flower monitoring, and dependency ordering.

```yaml
services:
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    command: redis-server --appendonly yes

  api:
    build: .
    depends_on:
      redis:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  worker_high:
    build: .
    depends_on:
      redis:
        condition: service_healthy
    command: celery -A app worker --queues=high --concurrency=4

  worker_low:
    build: .
    depends_on:
      redis:
        condition: service_healthy
    command: celery -A app worker --queues=low --concurrency=2

  flower:
    build: .
    depends_on:
      redis:
        condition: service_healthy
    command: celery -A app flower --port=5555
```

**Key design decisions:**
- **Redis healthcheck gates all services** — workers don't start before Redis is ready
- **Separate worker services per queue** — different concurrency per priority tier
- **Flower as dedicated service** — monitoring always available
- **Persistent Redis** via `appendonly yes` and named volume

**Adaptation notes:**
- Remove debug ports (5678, 5679) — not needed for production
- Remove SSL certificate volume mounts
- Remove `.env` file mounting (use environment variables in compose)
- Consolidate from 2 worker services (soap + httpx) to 2 (high + low)
- Add system deps for Pillow/pdfplumber in Dockerfile

**Target file:** `docker-compose.yml`

---

## Pattern 9: Client Library Architecture (Sync-Only)

**Source:** `ccee_queue_client/client.py`, `models.py`, `exceptions.py`

**Pattern:** Standalone HTTP client package with submit/poll/wait lifecycle, typed result models, and batch processing.

```python
# exceptions.py
class QueueClientError(Exception): ...
class TaskTimeoutError(QueueClientError):
    def __init__(self, task_id, timeout): ...
class TaskFailedError(QueueClientError):
    def __init__(self, task_id, error_message, error_details=None): ...
class APIConnectionError(QueueClientError):
    def __init__(self, base_url, original_error): ...

# models.py
@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    result: Optional[Dict] = None
    error: Optional[str] = None
    @property
    def is_success(self) -> bool: ...
    @property
    def is_failed(self) -> bool: ...

@dataclass
class BatchResult:
    total: int
    successful: int
    failed: int
    results: Dict[str, TaskResult]
    duration_seconds: float
    @property
    def success_rate(self) -> float: ...

# client.py
class Client:
    def __init__(self, base_url, default_timeout=300, default_priority='low'):
        self.session = requests.Session()
    def submit_task(self, endpoint, params, priority=None) -> str: ...
    def get_task_status(self, task_id) -> Dict: ...
    def wait_for_task(self, task_id, timeout, poll_interval=2, on_status_update=None) -> TaskResult: ...
    def batch_submit_and_wait(self, tasks, priority, poll_interval=2, timeout, on_progress) -> BatchResult: ...
    def check_health(self) -> bool: ...
```

**Key design decisions:**
- **Standalone package** — no imports from the server codebase
- **dataclasses for models** (not Pydantic) — lightweight, no extra dependency
- **requests.Session** for connection pooling
- **Status callback** (`on_status_update`) — allows progress reporting
- **Batch with index mapping** (`results_by_index`) — correlate results back to input order
- **Fixed poll interval** (no backoff) — 2-second constant interval

**Adaptation notes — Critical gaps identified:**
1. **No threading** — `wait_for_task()` and `batch_submit_and_wait()` block the calling thread entirely
2. **No exponential backoff** — fixed 2s poll interval wastes API calls for long-running jobs
3. **No Future API** — caller cannot do other work while waiting
4. **Shared session** — single `requests.Session` would cause issues in threaded use
5. **No context manager** — no `__enter__`/`__exit__` for resource cleanup
6. **No shutdown** — no way to terminate polling gracefully

**New client must add:**
- `ThreadPoolExecutor` with configurable `max_workers`
- `submit_async()` → returns `Future[JobResult]` immediately
- `submit_batch()` → returns `list[Future[JobResult]]`
- Exponential backoff: 0.5s → 1.0s → 2.0s → 4.0s → 5.0s (capped)
- Per-thread `requests.Session` for thread safety
- Context manager + `shutdown()` for lifecycle management

**Target file:** `client/client.py`, `client/poller.py`, `client/models.py`, `client/exceptions.py`

---

## Pattern 10: Port/Contract (ABC Interface)

**Source:** `core/contracts/gateways.py`

**Pattern:** Abstract base classes defining ports for external communication, enabling dependency inversion.

```python
from abc import ABC, abstractmethod

class IGateway(ABC):
    @abstractmethod
    def operation(self, params) -> Result:
        pass
```

**Key design decisions:**
- Pure ABCs with `@abstractmethod` — enforced at instantiation
- Typed method signatures — clear contracts for implementors
- Dependency inversion — core depends on abstractions, adapters implement them

**Adaptation notes:**
- Legacy gateways are domain-specific (measurements, obligations) — replace entirely
- New ports: `IFileProcessor` (process file → result dict) and `IJobStore` (CRUD for job metadata)
- Keep the ABC + `@abstractmethod` pattern exactly

**Target file:** `src/domain/ports/file_processor.py`, `src/domain/ports/job_store.py`

---

## Pattern 11: Pydantic Settings Configuration

**Source:** `config.py` + `core/queue_config.py`

**Pattern:** Two-tier configuration using Pydantic Settings — app-level settings and queue-specific settings, loaded from environment variables with defaults.

```python
class Settings(BaseSettings):
    app_name: str = "App Name"
    app_version: str = "1.0.0"
    debug: bool = False

    # External service URLs
    service_url: str = "https://..."

    # Timeouts
    http_timeout: int = 60
    http_max_retries: int = 3

    class Config:
        env_file = ".env"
        extra = "ignore"

class QueueConfig(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    redis_result_backend: str = "redis://localhost:6379/1"
    rate_limit: int = 60
    queue_high: str = "service_high"
    queue_low: str = "service_low"

    class Config:
        env_prefix = "QUEUE_"
        env_file = ".env"
        extra = "ignore"
```

**Key design decisions:**
- **Two config classes** — separation of concerns (app vs queue)
- **`extra = "ignore"`** — tolerates extra env vars without errors
- **Global singleton instances** — created at module level, imported everywhere
- **Env prefix** for queue config — avoids collision with other env vars

**Adaptation notes:**
- Merge into single config class for simplicity (app is smaller than legacy)
- Change env prefix to `TASKQUEUE_`
- Remove all legacy-specific settings (SOAP URLs, SSL paths, credentials)
- Add: `redis_job_store_url` (DB 2), `rate_limit_max_requests`, `job_result_ttl`

**Target file:** `src/infrastructure/config.py`

---

## Pattern 12: Custom Exception Hierarchy + FastAPI Handlers

**Source:** `core/models/errors.py`

**Pattern:** Domain exception hierarchy with HTTP status code mapping, `to_dict()` serialization, and registered FastAPI exception handlers.

```python
class AppException(Exception):
    def __init__(self, message, code=5000, detail=None, status_code=500):
        self.message = message
        self.code = code
        self.detail = detail
        self.status_code = status_code

    def to_dict(self):
        return {"error": {"message": self.message, "code": self.code, "detail": self.detail}}

class AuthError(AppException):
    def __init__(self, message="Auth error", detail=None):
        super().__init__(message=message, code=4001, detail=detail, status_code=401)

class ValidationError(AppException):
    def __init__(self, message="Validation error", detail=None):
        super().__init__(message=message, code=4000, detail=detail, status_code=400)

# FastAPI handler
async def app_exception_handler(request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

# Registration in main.py
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
```

**Key design decisions:**
- **Numeric error codes** alongside HTTP status — allows more granular error classification
- **`to_dict()`** method — consistent JSON error format across all exceptions
- **Registered at app level** — all unhandled exceptions get a clean JSON response
- **Generic handler** as catch-all — no stack traces leak to clients

**Adaptation notes:**
- Rename all classes: remove legacy prefix, use domain-specific names
- In hexagonal architecture, domain exceptions should NOT import FastAPI — keep handlers in adapter layer
- Domain exceptions: `DomainError`, `JobNotFoundError`, `ProcessingError`, `RateLimitExceededError`
- The `to_dict()` + handler pattern moves to middleware in `src/adapters/inbound/api/middleware.py`

**Target file:** `src/domain/exceptions.py` (domain errors) + `src/adapters/inbound/api/middleware.py` (handlers)

---

## Pattern 13: FastAPI Application Factory + Validation Handler

**Source:** `main.py`

**Pattern:** FastAPI app creation with CORS, exception handler registration, router inclusion, and custom validation error formatting.

```python
app = FastAPI(title="...", description="...", version="1.0.0")

# CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Custom validation error format
@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    missing = [e["loc"][-1] for e in exc.errors() if e["type"] == "missing"]
    return JSONResponse(status_code=422, content={"error": {"message": f"Missing {missing}"}})

# Routers
app.include_router(jobs_router)
app.include_router(monitoring_router)

# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
```

**Key design decisions:**
- **Custom validation error format** — converts Pydantic's verbose error JSON into human-readable messages
- **Centralized handler registration** — all error handling in one place
- **Health check at root** — immediate reachability test

**Adaptation notes:**
- Keep the pattern, update router imports
- Move to app factory function for testability: `def create_app() -> FastAPI`
- Add dependency injection wiring in factory
- Remove legacy router imports, add jobs + monitoring routers

**Target file:** `src/main.py`
