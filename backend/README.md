# Naga SIS Backend

## Quick Start (Local Dev)
This backend requires Dockerized Postgres to run locally; the test suite uses SQLite and does not require Docker.

- Prerequisites: Docker, Docker Compose, Python 3.13 with `uv` (for local commands).

- Option A — Full Docker (recommended):
  - `make run`
  - App available at http://localhost:8000

- Option B — Hybrid (Docker Postgres, local Django):
  - `make run MODE=hybrid`
  - This will start Postgres/Redis via Docker, run migrations, and serve Django locally.

### Service Control
- Stop containers: `make stop` (preserves volumes)
- Remove containers + volumes: `make down-clean` (destructive)
- Stream logs: `make logs` or `make logs SERVICE=django`
- Show last N lines without follow: `make logs-n N=500` (optionally add `SERVICE=django`)

## Tests (SQLite)
- Setup: `make setup`
- Run: `make test` (or `pytest -m "not slow"`)
- Coverage reports in `htmlcov/` (`make coverage` for HTML/XML)

## Contributor Guide
See `AGENTS.md` for project structure, style, testing, and PR guidelines.
