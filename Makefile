.PHONY: up down logs test lint shell worker-logs flower build clean

# ── Docker ──────────────────────────────────────────────────────────

up: ## Start all services
	docker compose up -d --build

down: ## Stop all services
	docker compose down

build: ## Build Docker images without starting
	docker compose build

logs: ## Tail logs from all services
	docker compose logs -f

worker-logs: ## Tail logs from workers only
	docker compose logs -f worker_high worker_low

flower: ## Open Flower monitoring UI
	@echo "Flower UI: http://localhost:5555"

shell: ## Open a shell in the API container
	docker compose exec api bash

clean: ## Stop services and remove volumes
	docker compose down -v

# ── Development ─────────────────────────────────────────────────────

test: ## Run unit tests
	pytest tests/unit/ -v

test-integration: ## Run integration tests (requires Redis + Celery)
	pytest tests/integration/ -v -m integration

test-all: ## Run all tests
	pytest tests/ -v

lint: ## Run linter
	ruff check src/ client/ tests/

format: ## Format code
	ruff format src/ client/ tests/

# ── Help ────────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
