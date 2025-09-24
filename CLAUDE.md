# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 CRITICAL: DOCKER-FIRST PROJECT 🚨

**This is a Docker-based project. PostgreSQL database ONLY runs in Docker containers.**

- ❌ **UV/pip commands that need database will FAIL** (no native PostgreSQL installed)
- ❌ **Any Django management command requiring database WILL FAIL**
- ✅ **Use Docker commands for ALL development operations**
- ✅ **UV commands only work for: linting, formatting, type checking, unit tests (SQLite)**

## 🚀 MCP SERVERS - USE THESE FIRST! 🚀

**Always prefer MCP servers over writing scripts. They save time and reduce errors.**

### Available MCP Servers:

1. **PostgreSQL MCP** (`postgresql://debug:debug@localhost:5432/naga_local`)
   - ✅ **USE FOR:** Database queries, table inspection, data analysis
   - ✅ **INSTEAD OF:** Writing Python scripts with Django ORM or Docker compose exec commands

2. **Context7 MCP** - Django documentation, API patterns, best practices
3. **GitHub MCP** - Repository operations, PR management, issue tracking  
4. **Playwright MCP** - Screenshots, browser automation, UI testing
5. **Filesystem MCP** - File operations, directory browsing

## Development Commands

### Nx Monorepo Commands (Recommended)

```bash
# Development
npm run dev                     # Start both backend and frontend
npm run dev:frontend           # Start frontend only
npm run dev:backend            # Start backend only

# Testing  
npm run test                   # All projects
npm run test:backend          # Backend only
npm run test:frontend         # Frontend only

# Run single test
npm run test:backend -- apps/finance/tests/test_models.py::TestFinanceModels::test_specific
npm run test:frontend -- src/components/MyComponent.spec.ts

# Code Quality
npm run lint                  # All projects
npm run format               # Format all projects
npm run typecheck           # TypeScript checking

# API Schema Management
npm run schema:generate      # Generate OpenAPI schema  
npm run schema:update        # Update TypeScript types

# Database Operations
npm run migrate             # Migrate database
npm run shell              # Django shell

# Nx Features
nx graph                   # View dependency graph
npm run affected:test      # Test only changed projects
```

### Backend Docker Commands

| Task | Docker Command (REQUIRED) | UV Command |
|------|---------------------------|------------|
| Dev Server | `docker compose -f docker-compose.local.yml up` | ❌ **FAILS** |
| Migrations | `docker compose -f docker-compose.local.yml run --rm django python manage.py migrate` | ❌ **FAILS** |
| Shell | `docker compose -f docker-compose.local.yml run --rm django python manage.py shell` | ❌ **FAILS** |
| Tests | `docker compose -f docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django pytest` | ✅ `uv run pytest` (SQLite only) |
| Lint/Format | `docker compose -f docker-compose.local.yml run --rm django ruff check` | ✅ `uv run ruff check` |

## Architecture

### Backend Clean Architecture (13 Django Apps)
```
Foundation Layer:    accounts/, common/
Core Domain:         people/, curriculum/, scheduling/, enrollment/  
Business Logic:      academic/, grading/, attendance/, finance/, scholarships/
Services:            academic_records/, level_testing/, language/
```

### Frontend (Vue 3 + Quasar + TypeScript)
- **Required:** TypeScript for API schema integration
- **Pattern:** Vue 3 Composition API + Quasar components only
- **Mobile:** PWA with offline-first design, Capacitor for native apps

### API Schema Sharing
```
Django Models → django-ninja → OpenAPI Schema → TypeScript Types → Vue Components
```

## Critical Rules (ZERO TOLERANCE)

### Architecture Alerts
**🚨 IMMEDIATELY STOP if detecting:**
- Circular dependencies between Django apps
- Mixed app responsibilities (single app handling multiple domains)
- Bidirectional dependencies (A imports B, B imports A)

### Docker Command Requirements
**🚨 DOCKER COMMANDS ONLY - NO EXCEPTIONS:**
- **❌ NEVER use `uv run python manage.py` commands that access PostgreSQL database**
- **❌ NEVER use `USE_DOCKER=no` for migrations, shell, or database operations**
- **✅ ALWAYS use `docker compose -f docker-compose.local.yml run --rm django` for ALL database operations**
- **✅ UV commands ONLY for: linting (`uv run ruff`), formatting, type checking, SQLite-only tests**

### Database Restrictions  
- **❌ NEVER make direct database schema changes** outside Django migrations
- **✅ ALL schema changes MUST go through Django migrations**
- **✅ ALL migration scripts MUST inherit from `BaseMigrationCommand`**

### Environment Protocol
- **LOCAL environment:** Primary development (use for ALL development work)
- **EVALUATION environment:** Remote demo only (never for development)

## Code Quality Standards

**Backend:**
- Python 3.13.7+ with comprehensive type hints
- **CRITICAL:** Never use f-strings in logging - use lazy formatting
- Ruff formatting (119 char line length)
- Google-style docstrings

**Frontend:**
- TypeScript REQUIRED for all new code
- Vue 3 Composition API only
- Quasar components over custom HTML
- Mobile-first responsive design

## Git Workflow

### Commit Message Format
Use this exact format when writing commits:

```
<emoji> <TYPE in ALL CAPS>: <short summary>
```

**Rules:**
- Start with one emoji that matches the change
- Keep summary ≤ 72 characters, imperative mood ("Add", "Fix", "Refactor")
- Add blank line + body if needed (wrapped to explain "what/why")
- Include ticket references in footer

**Emoji Map:**
```
✨ FEAT     → new feature
🐛 FIX      → bug fix  
🔒 SECURITY → security fix/hardening
📝 DOCS     → documentation only
♻️ REFACTOR → code refactor (no behavior change)
🚀 PERF     → performance improvement
✅ TEST     → tests
📦 BUILD    → build/dependencies
⚙️ CI       → CI/config
🔧 CHORE    → chores (no src/test changes)
```

**Examples:**
```
🔒 SECURITY: Harden URL configuration against regressions
🐛 FIX: Prevent crash on empty payload in payments worker
✨ FEAT: Add CSV export for enrollment report
```

- **⚠️ ALWAYS push to both repositories:** `git push origin main && git push gitlab main`

## Key File Locations

- **Django Apps:** `backend/apps/`
- **API Endpoints:** `backend/api/` (django-ninja)
- **Shared Types:** `libs/shared/api-types/`
- **Frontend Components:** `frontend/src/components/`
- **Project Documentation:** `backend/project-docs/`
- **Migration Data:** `backend/data/` (excluded from git)