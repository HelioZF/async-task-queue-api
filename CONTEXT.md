# Project Context — Async Task Queue API

> **Paste this into a new Claude chat to get instant project context.**

---

## Who I Am

I'm Helio, a backend-focused software engineer building a 6-project portfolio to showcase enterprise-grade Python/FastAPI skills. I have prior experience building queue systems for external API integrations in the energy sector. This portfolio rebuilds those real patterns in generic domains, stripping all proprietary code.

---

## What This Project Is

**Project 1 of 6** — A production-ready async job processing API where clients submit file processing tasks and get results asynchronously. Jobs have priorities (high/low), retry logic with exponential backoff, and are processed by distributed Celery workers.

**Domain:** File Processing Service (CSV summary, word count, image resize, PDF text extraction)

**Standout feature:** A **multi-threaded Python client library** (`concurrent.futures.ThreadPoolExecutor`) with Future-based API for non-blocking batch job submission.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web Framework | FastAPI ^0.115 |
| Task Queue | Celery ^5.4 |
| Message Broker | Redis 7 (Docker) |
| Data Validation | Pydantic v2 |
| Queue Monitoring | Flower ^2.0 |
| File Processing | pandas, Pillow, pdfplumber |
| Client Threading | concurrent.futures (stdlib) |
| Testing | pytest, pytest-asyncio, httpx |
| Containerization | Docker + docker-compose |
| Python | 3.11 |

---

## Key Files to Read First

| File | Purpose |
|------|---------|
| `DEVELOPMENT_LOG.md` | **Development audit trail** — project resume, progress tracker, session history, git strategy |
| `planner/AGENT_PIPELINE_PLAN.md` | **Agent pipeline plan** — 10 stages with seed prompts, acceptance criteria, dependencies |
| `planner/IMPLEMENTATION_PLAN.md` | Original technical plan — domain design, API spec, client library architecture (reference) |

---

## Development Method: AI Agent Pipeline

This project is built using the [AI Agent Orchestration Framework](../project4_ai-agent-orchestration-framework) — a 12-agent system with strict boundaries, filesystem-based communication, and audit trails.

### Pipeline Stages (10 total)

| Stage | Agent | Description |
|-------|-------|-------------|
| 0 | Code Analyst | Analyze legacy code, extract reusable patterns |
| 1 | Planner | Define domain: entities, ports, DTOs, exceptions, API contract |
| 2 | Backend | Build core: infrastructure, adapters, API routes, Celery tasks |
| 3 | Backend | Build client library (standalone, threaded) — star feature |
| 4 | Deploy | Docker, Compose, Makefile, scripts |
| 5 | QA | Unit, integration, E2E tests |
| 6 | Backend | Demo scripts + sample files |
| 7 | Docs | README, architecture docs, AI agent docs |
| 8 | QA | Final validation checklist |
| 9 | Process | Retrospective on pipeline execution |

**Current status:** See `DEVELOPMENT_LOG.md` for latest progress.

---

## Critical Rules

- **NEVER** reference "CCEE", "Lux", "Lux Energia", or any company name from the base code
- **NEVER** include real credentials, certificates, or internal URLs
- Base code in `base/` is reference only (gitignored) — extract **patterns**, not proprietary code
- `.env` must be in `.gitignore`; only `.env.example` with placeholders is committed
- Follow **Conventional Commits**: `feat(scope): description`
- Branch strategy: `main` -> `develop` -> `stage/*` branches

---

## Architecture Overview

```
POST /jobs → FastAPI Router → Celery task.apply_async(queue=jobs_high|jobs_low)
                                    ↓
                              Celery Worker → Dispatch to processor
                                    ↓
                              csv/text/image/pdf processor → Result in Redis (TTL: 1h)
                                    ↓
GET /jobs/{id} → Read result from Redis → Return to client
```

Two priority queues: `jobs_high` (4 workers) and `jobs_low` (2 workers).
No SQL database — Redis-only (broker DB 0, results DB 1, job store DB 2).

---

## How to Start Working

1. Read `DEVELOPMENT_LOG.md` — check current stage and last session notes
2. Read `planner/AGENT_PIPELINE_PLAN.md` — find the seed prompt for the current stage
3. Follow the pipeline: each stage has explicit inputs, outputs, write scope, and acceptance criteria
