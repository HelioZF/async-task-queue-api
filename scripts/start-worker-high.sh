#!/bin/bash
# Start Celery worker for the high-priority queue
celery -A src.infrastructure.celery_app worker \
    --queues=jobs_high \
    --concurrency=4 \
    --loglevel=info \
    --max-tasks-per-child=100 \
    --hostname=worker_high@%h
