#!/bin/bash

# validate-ci-locally.sh - Run CI/CD checks locally before pushing
# This simulates the GitLab CI pipeline to catch issues early

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}       Local CI/CD Validation - Naga SIS Backend${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Function to run a check
run_check() {
    local name="$1"
    local command="$2"

    echo -e "${YELLOW}▶ Running: $name${NC}"
    if eval "$command"; then
        echo -e "${GREEN}✓ $name passed${NC}\n"
        return 0
    else
        echo -e "${RED}✗ $name failed${NC}\n"
        return 1
    fi
}

# Track failures
FAILED_CHECKS=()

# Change to backend directory
cd "$BACKEND_DIR"

echo -e "${BLUE}Stage 1: Linting & Code Quality${NC}"
echo "────────────────────────────────────"

# 1. Ruff linting
if ! run_check "Ruff Check" "uv run ruff check apps/ config/ --output-format=concise"; then
    FAILED_CHECKS+=("Ruff Check")
fi

# 2. Ruff formatting
if ! run_check "Ruff Format Check" "uv run ruff format --check apps/ config/"; then
    FAILED_CHECKS+=("Ruff Format")
    echo -e "${YELLOW}  Tip: Run 'uv run ruff format apps/ config/' to auto-fix${NC}\n"
fi

# 3. Type checking
if ! run_check "MyPy Type Check" "uv run mypy apps/ --ignore-missing-imports"; then
    FAILED_CHECKS+=("MyPy")
fi

echo -e "${BLUE}Stage 2: Django Checks${NC}"
echo "────────────────────────────────────"

# 4. Django system check
if ! run_check "Django System Check" "DJANGO_SETTINGS_MODULE=config.settings.ci uv run python manage.py check"; then
    FAILED_CHECKS+=("Django Check")
fi

# 5. Check for missing migrations
if ! run_check "Django Migration Check" "DJANGO_SETTINGS_MODULE=config.settings.ci uv run python manage.py makemigrations --check --dry-run"; then
    FAILED_CHECKS+=("Missing Migrations")
    echo -e "${YELLOW}  Tip: Run 'docker compose -f docker-compose.local.yml run --rm django python manage.py makemigrations'${NC}\n"
fi

echo -e "${BLUE}Stage 3: Testing${NC}"
echo "────────────────────────────────────"

# 6. Run tests (using SQLite for speed in CI check)
if ! run_check "Unit Tests" "DJANGO_SETTINGS_MODULE=config.settings.test uv run pytest apps/ -x --tb=short -q"; then
    FAILED_CHECKS+=("Unit Tests")
fi

echo -e "${BLUE}Stage 4: Security & Dependencies${NC}"
echo "────────────────────────────────────"

# 7. Check for security issues
if ! run_check "Security Check (Bandit)" "uv run bandit -r apps/ -ll -q 2>/dev/null || true"; then
    FAILED_CHECKS+=("Security")
fi

# 8. Check dependencies
if ! run_check "Dependency Check" "uv pip check"; then
    FAILED_CHECKS+=("Dependencies")
fi

echo -e "${BLUE}Stage 5: Documentation & Files${NC}"
echo "────────────────────────────────────"

# 9. Check for large files
if ! run_check "Large File Check" "! find . -type f -size +1000k 2>/dev/null | grep -v '.git' | grep -v 'node_modules' | grep -v '.venv' | head -1 | grep ."; then
    FAILED_CHECKS+=("Large Files")
    echo -e "${YELLOW}  Found large files (>1MB). Consider using Git LFS or removing them.${NC}\n"
fi

# 10. Check for debugging code
if ! run_check "Debug Statement Check" "! grep -r 'import pdb\\|pdb.set_trace\\|breakpoint()\\|print(' apps/ --include='*.py' 2>/dev/null | head -5 | grep ."; then
    FAILED_CHECKS+=("Debug Statements")
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                        Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Safe to push.${NC}"
    exit 0
else
    echo -e "${RED}❌ Failed checks:${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo -e "   ${RED}• $check${NC}"
    done
    echo ""
    echo -e "${YELLOW}Fix these issues before pushing to avoid CI/CD failures.${NC}"
    echo -e "${YELLOW}You can still push with --no-verify if needed for WIP.${NC}"
    exit 1
fi
