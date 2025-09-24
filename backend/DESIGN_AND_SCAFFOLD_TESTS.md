ROLE: Senior Test Architect & Python/Django QA Lead

OBJECTIVE
Design and scaffold a comprehensive pytest-based test strategy for this monorepo:
- Heavy emphasis on UNIT TESTS.
- Smaller, targeted INTEGRATION TESTS.
- Focused CONTRACT/API TESTS.
All tests MUST use pytest (and pytest-django where applicable). We use Django-Ninja for APIs and uv for environment/install/run.

STACK HINTS (verify from repo):
- Django 5.x backend under apps/
- Django-Ninja APIs under api/
- Postgres, Redis, Dramatiq workers
- Docker-based local dev
- uv as the package/runner tool (not pip/poetry)

WHAT TO DO (NO SKIPPING):
1) **Inventory & Assumptions**
   - Inspect `apps/` and `api/`. List each app/service, purpose, key modules (models, services, views/routers, schemas, tasks).
   - Identify external boundaries (DB, cache, queues, outbound HTTP, email).
   - Locate Django-Ninja API object(s) and routing (e.g., `api/api.py`, `api/routers/*.py`).
   - Confirm OpenAPI availability (typically `/api/openapi.json`). Note exact paths or absence.
   - List high-risk domains (money, dates/time zones, permissions).

2) **Test Plan (markdown)**
   Include:
   - **Ratios**: many unit tests; fewer integration; a thin layer of contract/API tests.
   - **Coverage goals**: global ≥ 85%, critical modules ≥ 95% (call out justified exceptions).
   - **Layout**: per-package `tests/` mirroring source; subfolders `tests/unit`, `tests/integration`, `tests/contract`.
   - **Conventions**: AAA style, parametrization, fixtures, factories, boundary mocking, property tests with Hypothesis where valuable.
   - **Data & state**: `factory_boy` factories; `pytest-django` DB fixtures; `faker` for data; deterministic seeds.
   - **Isolation rules**: Unit tests mock DB/cache/network/queues; integration can use ephemeral DB/Redis; contract tests validate OpenAPI + representative flows.
   - **Dependencies**: minimal, pinned.
   - **Runtime**: parallelization (`-n auto`), fail on warnings where sensible.
   - **CI**: explicit stages/commands for `lint → unit → integration → contract → coverage`.
   - **Local dev**: `make test`, `make test-unit`, `make test-int`, `make test-api`, `make coverage`.
   - **Exit criteria** for replacing old suite.

3) **Tooling & Config**
   - Provide `pytest.ini` or `pyproject.toml` pytest block (test discovery, `addopts`, warnings policy).
   - Root `conftest.py` and per-app `conftest.py` as needed: DB fixture, settings overrides, time freeze helper, email outbox, faker session, HTTP mocking (`respx` for httpx).
   - Coverage config (`.coveragerc` or `pyproject.toml`) with include/omit rules.
   - **Django-Ninja test clients**:
     - For unit/contract tests against routers: `from ninja.testing import TestClient` bound to the `Api()` instance(s).
     - For integration (Django stack): Django’s `Client`/`APIRequestFactory` equivalents or `httpx` against a live ASGI app using `pytest-django`’s live server.
     - Prefer `httpx` + `respx` for outbound HTTP mocking.

4) **Contract/API Testing (Django-Ninja)**
   - Validate that `/api/openapi.json` is emitted and internally consistent (operationIds, schemas, required fields).
   - For each endpoint group, test status codes, content-types, and response shapes. Where feasible, assert against the OpenAPI schema (generate client or validate JSON schema).
   - Cover auth/permissions, invalid payloads, boundary sizes, pagination.

5) **Integration Tests**
   - Use `pytest-django` DB and ephemeral Redis. If available, propose `testcontainers`; otherwise provide a docker-compose override example.
   - Exercise key flows: ORM queries, signals/transactions, Dramatiq tasks (happy-path + one failure-path per critical flow).
   - Optionally run against `live_server` and `httpx.AsyncClient` with ASGI lifespan if app supports it.

6) **Unit Tests**
   - For every module in `apps/*` and `api/*`, create unit test skeletons (at least) with real examples for non-trivial logic (serializers/schemas, validators, permissions, services, utils).
   - Mock ALL externals at boundaries (DB, cache, network, queue). Keep fast (<100ms) and deterministic.

7) **Migration Plan for Existing Tests**
   - Do NOT delete immediately. Move old tests to `tests_legacy/`. Provide a checklist to prune after the new suite passes and coverage gates are met.

8) **Output Deliverables (produce now)**
   - `TEST_PLAN.md` (full details above).
   - `pytest.ini` or `pyproject.toml` test config.
   - Root `conftest.py` (+ per-package as needed).
   - Dev extras snippet for `pyproject.toml` or `requirements-dev.txt` including:
     - `pytest`, `pytest-django`, `factory_boy`, `faker`, `httpx`, `respx`, `freezegun`, `pytest-xdist`, `coverage`, `hypothesis`
   - `Makefile` targets.
   - Concrete unit tests for 2–3 representative apps.
   - Contract/API tests for 1 representative router, plus one integration test that hits DB and cache.

9) **Quality Bar (non-negotiable)**
   - No pseudo-code or TODOs. Use real imports/paths.
   - Deterministic seeds; no arbitrary sleeps.
   - Avoid over-mocking; mock only at boundaries.

10) **Commands (use uv)**
   - Install dev deps: `uv pip install -e .[dev]`
   - Run all tests: `uv run pytest -q`
   - Unit only: `uv run pytest -q tests/unit`
   - Integration (parallel): `uv run pytest -q tests/integration -n auto`
   - Contract/API: `uv run pytest -q tests/contract`
   - Coverage: `uv run pytest --cov=apps --cov=api --cov-report=term-missing`
   - Provide a GitHub Actions or GitLab CI example with uv caching and coverage gates (fail if <85%).

CONSTRAINTS
- If uncertain, FIRST list the uncertainty and propose a default, then proceed.
- Do not hallucinate paths/files—discover and print exact ones.
- Prefer small, composable fixtures over mega-fixtures.
- Keep dependencies minimal and mainstream.

BEGIN by:
- Printing the discovered app list with paths.
- Printing the external boundary list.
- Then emit `TEST_PLAN.md`, config files, and example tests.

END with:
- A 10–15 item adoption checklist for the team.