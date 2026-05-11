# Domain Model — Async Task Queue API

> **Stage 1 — Planner Agent**
> Domain model documentation for the File Processing Service.

---

## Class Diagram

```mermaid
classDiagram
    direction TB

    class Job {
        +str job_id
        +JobType job_type
        +JobPriority priority
        +JobStatus status
        +dict payload
        +dict? result
        +str? error
        +datetime created_at
        +datetime? completed_at
        +int retry_count
        +int max_retries
        +mark_processing()
        +mark_success(result)
        +mark_failed(error)
        +mark_cancelled()
        +increment_retry() bool
        +is_terminal bool
        +is_cancellable bool
    }

    class JobStatus {
        <<enumeration>>
        PENDING
        PROCESSING
        SUCCESS
        FAILED
        CANCELLED
    }

    class JobPriority {
        <<enumeration>>
        LOW
        HIGH
    }

    class JobType {
        <<enumeration>>
        CSV_SUMMARY
        WORD_COUNT
        IMAGE_RESIZE
        PDF_EXTRACT
    }

    class IFileProcessor {
        <<interface>>
        +supported_job_type JobType*
        +process(payload) dict*
    }

    class IJobStore {
        <<interface>>
        +save(job)*
        +get(job_id) Job?*
        +update_status(job_id, status, result?, error?)*
        +list_recent(limit) list~Job~*
        +delete(job_id) bool*
    }

    class DomainError {
        +str message
    }
    class JobNotFoundError {
        +str job_id
    }
    class ProcessingError {
        +str? job_type
    }
    class InvalidPayloadError
    class RateLimitExceededError {
        +str resource
    }
    class JobCancelledError {
        +str job_id
    }

    Job --> JobStatus
    Job --> JobPriority
    Job --> JobType
    IFileProcessor --> JobType
    IJobStore --> Job
    IJobStore --> JobStatus

    DomainError <|-- JobNotFoundError
    DomainError <|-- ProcessingError
    DomainError <|-- InvalidPayloadError
    DomainError <|-- RateLimitExceededError
    DomainError <|-- JobCancelledError
```

---

## Job Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> PENDING : submit job
    PENDING --> PROCESSING : worker picks up
    PENDING --> CANCELLED : client cancels
    PROCESSING --> SUCCESS : processor completes
    PROCESSING --> FAILED : processor error (retries exhausted)
    PROCESSING --> PROCESSING : retry (within max_retries)
    PROCESSING --> CANCELLED : client cancels
    SUCCESS --> [*]
    FAILED --> [*]
    CANCELLED --> [*]
```

---

## Layer Responsibilities

| Layer | Contents | Dependencies |
|-------|----------|--------------|
| **Domain** (`src/domain/`) | Job entity, enums, ports (ABCs), exceptions | None (pure Python) |
| **Application** (`src/application/`) | DTOs (Pydantic), use cases, mappers | Domain only |
| **Adapters** (`src/adapters/`) | FastAPI routes, Redis store, file processors | Application + Domain |
| **Infrastructure** (`src/infrastructure/`) | Celery, Redis client, config, rate limiter | Application + Domain |

**Dependency rule (inviolable):** `domain/ ← application/ ← adapters/` — domain imports nothing external.

---

## File Locations

| Artifact | File | Type |
|----------|------|------|
| Job entity | `src/domain/entities/job.py` | `@dataclass` |
| JobStatus, JobPriority, JobType | `src/domain/value_objects/enums.py` | `str, Enum` |
| IFileProcessor | `src/domain/ports/file_processor.py` | `ABC` |
| IJobStore | `src/domain/ports/job_store.py` | `ABC` |
| Domain exceptions | `src/domain/exceptions.py` | `Exception` subclasses |
| Request/Response DTOs | `src/application/dtos/job_dtos.py` | Pydantic `BaseModel` |
