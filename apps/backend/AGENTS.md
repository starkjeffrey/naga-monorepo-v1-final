# Repository Guidelines

## Project Structure & Module Organization
- `apps/`: Django apps (e.g., `finance/`, `academic/`, `users/`). Keep domain logic inside each app.
- `api/v1/`: Django Ninja API routers, schemas, and tests.
- `config/`: Project settings (`config/settings/*.py`), URLs, ASGI/WSGI.
- `tests/`: Central test suite (`unit/`, `integration/`, `contract/`). App-specific tests may also live in `apps/*/tests`.
- `scripts/`, `compose/`, `Dockerfile`: Ops/dev tooling. Static and templates under `static/` and `templates/`.

## Build, Test, and Development Commands
- `make setup`: Install dev/test deps via `uv` and prep folders.
- `make fmt` / `make lint` / `make typecheck`: Format (Ruff), lint (Ruff), and type-check (mypy).
- `make test-fast` | `make test` | `make coverage`: Quick unit slice, full suite with coverage, or HTML/XML reports (`htmlcov/`).
- Local run (Dockerized Postgres required):
  - Full Docker: `docker compose -f docker-compose.local.yml up -d` (Django at http://localhost:8000).
  - Hybrid: `docker compose -f docker-compose.local.yml up -d postgres redis` then
    `export DATABASE_URL=postgres://debug:debug@localhost:5432/naga_local` and
    `DJANGO_SETTINGS_MODULE=config.settings.local uv run python manage.py runserver 0.0.0.0:8000`.
- One-off Django cmds: `uv run python manage.py migrate` / `createsuperuser`.

## Coding Style & Naming Conventions
- Python 3.13; formatter: Ruff (line length 119, double quotes); imports managed by Ruff/isort.
- Typing: mypy with Django stubs; stricter in `services/` and utilities.
- Indentation: 4 spaces. Names: modules `snake_case`, classes `PascalCase`, functions/tests `snake_case`.
- Keep apps cohesive; prefer `apps.<domain>.services` over fat models/views.

## Testing Guidelines
- Framework: pytest + pytest-django; DB reuse enabled.
- Markers: `unit`, `integration`, `contract`, `e2e`, `slow`, `security`, etc. Example: `pytest -m "not slow"`.
- Coverage: ≥ 85% enforced in CI (`pytest.ini`/`make coverage-check`).
- Layout: place new tests in `tests/unit|integration|contract` or `apps/<app>/tests`. Name files `test_*.py`.

## Commit & Pull Request Guidelines
- Commits: short, present-tense, scoped. Emoji + TYPE prefix common (e.g., `🧪 TEST: ...`, `♻️ REFACTOR: ...`).
- PRs: clear description, linked issues, rationale, and testing notes. Include API examples for `api/v1` changes.
- Quality gates: run `make pre-commit` locally; CI runs lint, type-check, tests, and coverage.
- Migrations: commit deterministic migrations; separate large refactors from behavior changes.

## Security & Configuration Tips
- Secrets via environment (`.envs/`, `.env.ci`, `.env.eval`); never commit secrets.
- Settings are environment-specific (`config.settings.local|test|production`).
- Redis/queues and ASGI/Channels are used; prefer fakes in tests (`fakeredis`, markers like `requires_redis`).
- Optional: use `docker-compose.local.yml` for containers if your setup requires it.
