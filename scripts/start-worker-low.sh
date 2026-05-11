#!/bin/bash
# Start Celery worker for the low-priority queue
celery -A src.infrastructure.celery_app worker \
    --queues=jobs_low \
    --concurrency=2 \
    --loglevel=info \
    --max-tasks-per-child=100 \
    --hostname=worker_low@%h
