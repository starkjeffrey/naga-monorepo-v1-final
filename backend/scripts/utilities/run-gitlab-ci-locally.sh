#!/bin/bash

# run-gitlab-ci-locally.sh - Run GitLab CI pipeline locally using Docker
# This runs the EXACT same pipeline as GitLab CI/CD to save money on CI minutes

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}       GitLab CI Local Runner - Save CI/CD Minutes!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if gitlab-runner is installed
if ! command -v gitlab-runner &> /dev/null; then
    echo -e "${YELLOW}GitLab Runner not found. Installing...${NC}"
    echo ""
    echo "Choose your installation method:"
    echo "1) Docker (recommended - no system changes)"
    echo "2) Homebrew (macOS)"
    echo "3) Manual"
    read -p "Choice (1-3): " choice

    case $choice in
        1)
            echo -e "${BLUE}Using Docker to run GitLab CI...${NC}"
            USE_DOCKER=true
            ;;
        2)
            echo -e "${BLUE}Installing via Homebrew...${NC}"
            brew install gitlab-runner
            ;;
        3)
            echo "Visit: https://docs.gitlab.com/runner/install/"
            exit 1
            ;;
    esac
fi

# Get the project root (monorepo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONOREPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

cd "$MONOREPO_ROOT"

# Function to run with Docker
run_with_docker() {
    echo -e "${BLUE}Running GitLab CI pipeline locally with Docker...${NC}"

    docker run --rm \
        -v "$MONOREPO_ROOT:/builds/project" \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -w /builds/project \
        --privileged \
        gitlab/gitlab-runner:latest \
        exec docker \
        --docker-image python:3.13-slim \
        --docker-volumes /var/run/docker.sock:/var/run/docker.sock \
        bash -c "
            cd /builds/project/backend
            apt-get update && apt-get install -y git curl
            curl -LsSf https://astral.sh/uv/install.sh | sh
            source \$HOME/.local/bin/env
            uv sync

            echo '🔍 Running Lint Stage...'
            uv run ruff check apps/ config/ --output-format=concise
            uv run ruff format --check apps/ config/

            echo '🧪 Running Test Stage...'
            DJANGO_SETTINGS_MODULE=config.settings.test uv run pytest apps/ -x

            echo '✅ All checks passed!'
        "
}

# Function to run with local gitlab-runner
run_with_local_runner() {
    echo -e "${BLUE}Running GitLab CI pipeline locally...${NC}"

    # Check which jobs to run
    echo "Which job(s) to run?"
    echo "1) All jobs"
    echo "2) Lint only"
    echo "3) Test only"
    echo "4) Specific job (you'll enter the name)"
    read -p "Choice (1-4): " job_choice

    case $job_choice in
        1)
            JOB_NAME=""
            ;;
        2)
            JOB_NAME="lint:backend"
            ;;
        3)
            JOB_NAME="test:backend"
            ;;
        4)
            read -p "Enter job name: " JOB_NAME
            ;;
    esac

    # Run the pipeline
    if [ -z "$JOB_NAME" ]; then
        gitlab-runner exec docker \
            --docker-image python:3.13-slim \
            --docker-volumes "$MONOREPO_ROOT:/builds/project:rw" \
            --env "CI_PROJECT_DIR=/builds/project"
    else
        gitlab-runner exec docker "$JOB_NAME" \
            --docker-image python:3.13-slim \
            --docker-volumes "$MONOREPO_ROOT:/builds/project:rw" \
            --env "CI_PROJECT_DIR=/builds/project"
    fi
}

# Main execution
if [ "$USE_DOCKER" = true ] || [ "$1" = "--docker" ]; then
    run_with_docker
else
    run_with_local_runner
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Local CI run complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}💡 Tips to save CI/CD costs:${NC}"
echo -e "   • Run this script before every push"
echo -e "   • Use --docker flag to avoid installing gitlab-runner"
echo -e "   • Fix issues locally instead of using CI/CD for debugging"
echo -e "   • Consider git hooks: cp scripts/utilities/pre-push-hook.sh .git/hooks/pre-push"
