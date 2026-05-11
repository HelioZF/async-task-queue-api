# API Contract — Async Task Queue API

> **Stage 1 — Planner Agent**
> Complete API specification with request/response examples for all endpoints.

---

## Base URL

```
http://localhost:8000
```

---

## Endpoints Overview

| Method | Path | Description | Status Code |
|--------|------|-------------|-------------|
| `POST` | `/jobs` | Submit a new file processing job | `202 Accepted` |
| `GET` | `/jobs/{job_id}` | Get job status and result | `200 OK` |
| `DELETE` | `/jobs/{job_id}` | Cancel a pending/processing job | `200 OK` |
| `GET` | `/jobs` | List recent jobs | `200 OK` |
| `GET` | `/health` | Health check (Redis, workers, queues) | `200 OK` |
| `GET` | `/queue/stats` | Queue statistics and rate limit status | `200 OK` |

---

## POST /jobs — Submit Job

Submit a file processing job to the queue.

**Request:**
```json
{
  "job_type": "csv_summary",
  "priority": "high",
  "payload": {
    "file_content": "bmFtZSxhbW91bnQsZGF0ZQpBbGljZSwxMDAsMjAyNS0wMS0wMQ==",
    "filename": "sales.csv"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `job_type` | string | Yes | One of: `csv_summary`, `word_count`, `image_resize`, `pdf_extract` |
| `priority` | string | No | `high` or `low` (default: `low`) |
| `payload.file_content` | string | Yes | Base64-encoded file content |
| `payload.filename` | string | Yes | Original filename with extension |

**Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "priority": "high",
  "message": "Job submitted successfully.",
  "check_status_url": "/jobs/550e8400-e29b-41d4-a716-446655440000",
  "estimated_time": "5-15 seconds"
}
```

**Error Responses:**
| Status | Condition |
|--------|-----------|
| `422` | Invalid `job_type`, missing `payload`, or validation error |
| `429` | Rate limit exceeded |

---

## GET /jobs/{job_id} — Get Job Status

Poll for the current status of a submitted job.

**Response — Pending (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "job_type": "csv_summary",
  "result": null,
  "error": null,
  "created_at": "2025-06-01T10:00:00Z",
  "completed_at": null,
  "retry_count": 0
}
```

**Response — Success (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "job_type": "csv_summary",
  "result": {
    "row_count": 1500,
    "columns": ["name", "amount", "date"],
    "column_stats": {
      "amount": {"min": 10.0, "max": 9999.0, "mean": 450.5}
    },
    "preview": [
      {"name": "Alice", "amount": 100, "date": "2025-01-01"}
    ]
  },
  "error": null,
  "created_at": "2025-06-01T10:00:00Z",
  "completed_at": "2025-06-01T10:00:07Z",
  "retry_count": 0
}
```

**Response — Failed (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "job_type": "csv_summary",
  "result": null,
  "error": "Invalid CSV format: no columns found",
  "created_at": "2025-06-01T10:00:00Z",
  "completed_at": "2025-06-01T10:00:03Z",
  "retry_count": 3
}
```

**Error Responses:**
| Status | Condition |
|--------|-----------|
| `404` | Job ID not found |

---

## DELETE /jobs/{job_id} — Cancel Job

Cancel a job that is pending or processing.

**Response — Cancelled (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Job cancelled successfully.",
  "previous_status": "pending"
}
```

**Response — Not Cancellable (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "message": "Job cannot be cancelled (already in terminal state).",
  "previous_status": "success"
}
```

**Error Responses:**
| Status | Condition |
|--------|-----------|
| `404` | Job ID not found |

---

## GET /jobs — List Recent Jobs

List the most recently submitted jobs.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 20 | Max number of jobs to return |

**Response (200):**
```json
{
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "success",
      "job_type": "csv_summary",
      "result": {"row_count": 1500},
      "error": null,
      "created_at": "2025-06-01T10:00:00Z",
      "completed_at": "2025-06-01T10:00:07Z",
      "retry_count": 0
    }
  ],
  "total": 1
}
```

---

## GET /health — Health Check

Returns the health status of all system components.

**Response (200):**
```json
{
  "status": "healthy",
  "components": {
    "redis": "healthy",
    "workers": "healthy (2 workers active)",
    "queues": "healthy"
  }
}
```

---

## GET /queue/stats — Queue Statistics

Returns detailed metrics about the queue system.

**Response (200):**
```json
{
  "workers": {
    "total": 2,
    "stats": {}
  },
  "tasks": {
    "active": 1,
    "scheduled": 0,
    "reserved": 3
  },
  "queue_depths": {
    "jobs_high": 2,
    "jobs_low": 15
  },
  "rate_limiting": {
    "file_processing": {
      "current_count": 12,
      "limit": 60,
      "window": "60s",
      "available": 48
    }
  }
}
```

---

## Processor Output Schemas

### csv_summary
```json
{
  "row_count": 1500,
  "columns": ["name", "amount", "date"],
  "column_stats": {
    "amount": {"min": 10.0, "max": 9999.0, "mean": 450.5}
  },
  "preview": [
    {"name": "Alice", "amount": 100, "date": "2025-01-01"}
  ]
}
```

### word_count
```json
{
  "total_words": 850,
  "unique_words": 312,
  "line_count": 45,
  "top_10_words": [
    {"word": "the", "count": 42},
    {"word": "and", "count": 28}
  ]
}
```

### image_resize
```json
{
  "original_size": {"width": 1920, "height": 1080},
  "new_size": {"width": 800, "height": 450},
  "format": "PNG",
  "resized_content": "<base64-encoded-image>"
}
```

### pdf_extract
```json
{
  "page_count": 5,
  "total_chars": 12500,
  "extracted_text": "First 5000 characters of extracted text..."
}
```

---

## Error Response Format

All errors follow a consistent structure:

```json
{
  "error": {
    "message": "Human-readable error description",
    "code": 4000,
    "detail": "Optional additional context"
  }
}
```

| Code | Meaning |
|------|---------|
| `4000` | Validation error |
| `4004` | Not found |
| `4029` | Rate limit exceeded |
| `5000` | Internal server error |
