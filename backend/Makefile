# Makefile — Naga SIS Backend (Consolidated)
# Streamlined test + quality + coverage + docker helpers

# =====================
# Variables
# =====================
PYTHON  := uv run python
PYTEST  := uv run pytest
RUFF    := uv run ruff
MYPY    := uv run mypy
DJANGO  := $(PYTHON) manage.py

# Directories
APP_DIR := apps
API_DIR := api
TEST_DIR := tests

# Coverage thresholds
COVERAGE_THRESHOLD := 85
CRITICAL_COVERAGE_THRESHOLD := 95

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

# Default target
.DEFAULT_GOAL := help

# Ensure phony targets

.PHONY: help setup install-test fmt fmt-core fmt-all lint lint-core lint-all typecheck typecheck-core typecheck-all typecheck-attr-report quality \
	test test-fast test-unit test-int test-api test-e2e test-quick \
	coverage coverage-check coverage-html clean-test clean-all \
	pre-commit pre-push ci test-all test-critical test-profile \
	test-failed test-changed test-list test-parallel \
	test-docker test-docker-build run run-docker run-hybrid stop down-clean logs logs-n bundle

# =====================
# HELP
# =====================
help: ## Show help for all commands
	@echo "$(GREEN)Naga SIS Backend — Commands$(NC)"; echo
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo; echo "$(GREEN)Quick start:$(NC) make setup && make test-fast"

# =====================
# SETUP
# =====================
install-test: ## Install test/dev dependencies
	@echo "$(GREEN)Installing test dependencies...$(NC)"
	uv pip install -e .[test]

setup: install-test ## Full setup for dev/test
	@mkdir -p htmlcov backups $(TEST_DIR)/logs
	@echo "$(GREEN)Setup complete.$(NC)"

# =====================
# CODE QUALITY
# =====================
fmt: fmt-core ## Format Python code (ruff formatter)

fmt-core: ## Format shipped code only (apps/api/tests)
	$(RUFF) format $(APP_DIR) $(API_DIR) $(TEST_DIR)

fmt-all: ## Format entire repository (all Python files)
	$(RUFF) format .

lint: lint-core ## Lint Python (ruff check) — shipped code only

lint-core: ## Lint shipped code only (apps/api/tests)
	$(RUFF) check $(APP_DIR) $(API_DIR) $(TEST_DIR)

lint-all: ## Lint entire repository (all Python files)
	$(RUFF) check .

typecheck: typecheck-core ## Type-check with mypy (shipped code)

typecheck-core: ## Type-check shipped code only (apps/api)
	$(MYPY) $(APP_DIR) $(API_DIR)

typecheck-all: ## Type-check entire repository
	$(MYPY) .

typecheck-attr-report: ## Report mypy [attr-defined] counts by file for apps/api
	bash scripts/utilities/mypy_attr_defined_report.sh

quality: lint typecheck ## Run all quality checks
	@echo "$(GREEN)Quality checks passed.$(NC)"

# =====================
# TESTS
# =====================
# Notes:
# - Keep markers simple: unit/integration/contract/e2e/slow
# - Parallelization via -n auto (pytest-xdist)

test-fast: ## Fast subset (unit, no slow)
	$(PYTEST) -q $(TEST_DIR)/unit -n auto -m "not slow"

test-unit: ## All unit tests (parallel)
	$(PYTEST) -q $(TEST_DIR)/unit -n auto

test-int: ## Integration tests
	$(PYTEST) -q $(TEST_DIR)/integration -n auto

test-api: ## API contract tests
	$(PYTEST) -q $(TEST_DIR)/contract

test-e2e: ## End-to-end tests
	$(PYTEST) -q $(TEST_DIR)/e2e -m "e2e"

test-quick: ## Very fast sanity check during dev
	$(PYTEST) -q -x --ff $(TEST_DIR)/unit -m "not slow"

test-failed: ## Re-run only failed tests
	$(PYTEST) -q --lf

test-parallel: ## Max parallelization across the suite
	$(PYTEST) -q -n auto --dist loadscope

# Canonical complete test run with coverage (backend only)
# Adjust as needed once API tests live elsewhere

test: ## All tests with coverage (apps + api)
	$(PYTEST) -q --cov=$(APP_DIR) --cov=$(API_DIR) --cov-report=term-missing

# =====================
# COVERAGE & REPORTS
# =====================
coverage: ## HTML + XML coverage reports
	$(PYTEST) --cov=$(APP_DIR) --cov=$(API_DIR) \
		--cov-report=html:htmlcov \
		--cov-report=term-missing \
		--cov-report=xml
	@echo "$(GREEN)Open htmlcov/index.html for the report.$(NC)"

coverage-check: ## Enforce minimum coverage threshold
	$(PYTEST) --cov=$(APP_DIR) --cov=$(API_DIR) \
		--cov-report=term-missing \
		--cov-fail-under=$(COVERAGE_THRESHOLD)

coverage-html: coverage ## Open coverage report in browser
	@if command -v xdg-open >/dev/null; then xdg-open htmlcov/index.html; \
	elif command -v open >/dev/null; then open htmlcov/index.html; \
	else echo "Open htmlcov/index.html manually"; fi

# =====================
# SPECIALIZED TEST SETS
# =====================
# Keep one focused critical set; expand only if truly needed

test-critical: ## Critical business areas (finance, academic, auth)
	$(PYTEST) -q apps/finance/tests apps/academic/tests apps/accounts/tests \
		--cov=apps/finance --cov=apps/academic --cov=apps/accounts \
		--cov-fail-under=$(CRITICAL_COVERAGE_THRESHOLD)

# =====================
# CI / GIT HOOK ENTRYPOINTS
# =====================
pre-commit: ## What runs locally before committing
	$(MAKE) fmt
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test-fast
	@echo "$(GREEN)pre-commit passed.$(NC)"

pre-push: ## Gatekeeper before pushing to remote
	$(MAKE) quality
	$(MAKE) coverage-check
	@echo "$(GREEN)pre-push passed.$(NC)"

ci: ## CI pipeline parity (lint + typecheck + full tests)
	$(MAKE) fmt
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test
	$(MAKE) coverage-check

# Roll-up target
test-all: quality test coverage-check ## Full suite + quality gates
	@echo "$(GREEN)All tests and checks passed!$(NC)"

# =====================
# CLEANUP
# =====================
clean-test: ## Remove test/coverage artifacts
	rm -rf .pytest_cache/ htmlcov/ .coverage coverage.xml test-results.xml test-report.html $(TEST_DIR)/logs/*.log || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)Cleaned test artifacts.$(NC)"

clean-all: clean-test ## Also remove tool caches
	rm -rf build/ dist/ *.egg-info .mypy_cache/ .ruff_cache/
	@echo "$(GREEN)Cleaned all build artifacts.$(NC)"

# =====================
# DOCKER (adjust to your dev/dev/prod files later)
# =====================
# You mentioned you have dev/dev/prod variants; stub targets below
# Update compose files or use env vars when you finalize naming

test-docker-build: ## Build Docker test image
	docker compose -f docker-compose.test.yml build test

test-docker: ## Run tests in Docker
	docker compose -f docker-compose.test.yml run --rm test

# =====================
# RUN (Local Development)
# =====================
# Supports full-Docker and hybrid modes. Use MODE=hybrid to run Django locally
# against Dockerized Postgres/Redis. Default is full Docker.

COMPOSE_FILE ?= docker-compose.local.yml

run: ## Start app (MODE=docker|hybrid, default: docker)
	@if [ "$(MODE)" = "hybrid" ]; then \
		$(MAKE) run-hybrid; \
	else \
		$(MAKE) run-docker; \
	fi

run-docker: ## Full Docker dev stack (Django, Postgres, Redis, Mailpit)
	docker compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)Django available at http://localhost:8000$(NC)"

run-hybrid: ## Dockerized Postgres/Redis + local Django via uv
	docker compose -f $(COMPOSE_FILE) up -d postgres redis
	@echo "Waiting for Postgres health..."; \
	until [ "$$(docker inspect -f '{{.State.Health.Status}}' naga_local_postgres 2>/dev/null || echo starting)" = "healthy" ]; do \
	  printf "."; sleep 2; \
	done; echo
	@echo "$(GREEN)Postgres is healthy. Running migrations...$(NC)"
	DATABASE_URL=postgres://debug:debug@localhost:5432/naga_local \
	DJANGO_SETTINGS_MODULE=config.settings.local \
		$(PYTHON) manage.py migrate
	@echo "$(GREEN)Starting Django locally at http://localhost:8000$(NC)"
	DATABASE_URL=postgres://debug:debug@localhost:5432/naga_local \
	DJANGO_SETTINGS_MODULE=config.settings.local \
		$(PYTHON) manage.py runserver 0.0.0.0:8000

# =====================
# SERVICE CONTROL
# =====================
stop: ## Stop and remove dev containers (docker compose down)
	docker compose -f $(COMPOSE_FILE) down
	@echo "$(YELLOW)Stopped containers for $(COMPOSE_FILE). Volumes preserved.$(NC)"

logs: ## Stream logs (use SERVICE=name to filter, e.g., SERVICE=django)
	docker compose -f $(COMPOSE_FILE) logs -f --tail=200 $(SERVICE)

down-clean: ## Stop containers and remove volumes (DANGER: data loss)
	docker compose -f $(COMPOSE_FILE) down -v --remove-orphans
	@echo "$(RED)Containers and volumes removed for $(COMPOSE_FILE).$(NC)"

logs-n: ## Show last N lines without follow (N=200, SERVICE=optional)
	N=$${N:-200}; \
	docker compose -f $(COMPOSE_FILE) logs --tail=$$N $(SERVICE)

# =====================
# SAFETY NETS
# =====================
bundle: ## Create a portable git bundle backup in ./backups/
	@mkdir -p backups
	git bundle create backups/naga-$(shell date +%F).bundle --all
	@echo "$(GREEN)Bundle created at backups/naga-$(shell date +%F).bundle$(NC)"

.PHONY: qa-baseline qa-ratchet

qa-baseline: ## Write current counts as new baselines (use after big cleanup)
	@mkdir -p qa/baselines
	@echo "Computing baselines..."
	@# Ruff
	@count=$$(uv run ruff check apps api tests | grep -E '^[^:]+:[0-9]+:[0-9]+:' | wc -l | tr -d ' '); \
	echo $$count > qa/baselines/ruff.txt; echo "Ruff baseline: $$count"
	@# Mypy
	@count=$$(uv run mypy apps api | grep -c 'error:' || true); \
	echo $$count > qa/baselines/mypy.txt; echo "Mypy baseline: $$count"
	@# Coverage
	@uv run pytest -q --cov=apps --cov=api --cov-report=term --cov-report=xml || true
	@pct=$$(uv run coverage report --fail-under=0 | tail -n 1 | awk '{print $$NF}' | tr -d '%'); \
	echo $$pct > qa/baselines/coverage.txt; echo "Coverage baseline: $$pct%"

qa-ratchet: ## Enforce no regressions vs baselines
	@./qa/ratchet.sh
	
