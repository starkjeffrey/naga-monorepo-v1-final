#!/bin/bash
# Migration Environment Management Script
# Provides fool-proof commands for managing migration environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Function to check if migration environment is running
check_migration_env() {
    if docker compose -f docker-compose.migration.yml ps | grep -q "Up"; then
        return 0
    else
        return 1
    fi
}

# Function to wait for services to be healthy
wait_for_services() {
    print_step "Waiting for services to be ready..."
    local max_attempts=60
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker compose -f docker-compose.migration.yml exec django python manage.py check --database=default > /dev/null 2>&1; then
            print_status "Services are ready!"
            return 0
        fi

        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    print_error "Services failed to start within expected time"
    return 1
}

# Main command dispatcher
case "${1:-help}" in
    "start")
        print_status "🚀 Starting migration environment..."

        # Check if local environment is running
        if docker compose -f docker-compose.local.yml ps | grep -q "Up"; then
            print_warning "Local environment is running. Consider stopping it to avoid port conflicts."
            read -p "Stop local environment? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                print_step "Stopping local environment..."
                docker compose -f docker-compose.local.yml down
            fi
        fi

        # Start migration environment
        print_step "Starting migration services..."
        docker compose -f docker-compose.migration.yml up -d

        # Wait for services
        wait_for_services

        # Set up environment
        print_step "Setting up migration environment..."
        docker compose -f docker-compose.migration.yml exec django python manage.py setup_migration_environment

        print_status "✅ Migration environment is ready!"
        echo ""
        echo "Access points:"
        echo "  - Django: http://localhost:8001"
        echo "  - Mailpit: http://localhost:8026"
        echo "  - Flower: http://localhost:5556"
        echo "  - PostgreSQL: localhost:5433"
        echo ""
        echo "Next steps:"
        echo "  - Run 'bash scripts/migration-env.sh migrate-legacy' to import legacy data"
        echo "  - Run 'bash scripts/migration-env.sh shell' to access Django shell"
        ;;

    "stop")
        print_status "🛑 Stopping migration environment..."
        docker compose -f docker-compose.migration.yml down
        print_status "✅ Migration environment stopped"
        ;;

    "restart")
        print_status "🔄 Restarting migration environment..."
        docker compose -f docker-compose.migration.yml down
        docker compose -f docker-compose.migration.yml up -d
        wait_for_services
        print_status "✅ Migration environment restarted"
        ;;

    "status")
        print_status "📊 Migration environment status:"
        docker compose -f docker-compose.migration.yml ps
        ;;

    "logs")
        shift
        docker compose -f docker-compose.migration.yml logs -f "$@"
        ;;

    "shell")
        if ! check_migration_env; then
            print_error "Migration environment is not running. Start it with: bash scripts/migration-env.sh start"
            exit 1
        fi
        docker compose -f docker-compose.migration.yml exec django python manage.py shell
        ;;

    "migrate-legacy")
        if ! check_migration_env; then
            print_error "Migration environment is not running. Start it with: bash scripts/migration-env.sh start"
            exit 1
        fi

        print_status "🔄 Starting legacy data migration..."
        shift
        docker compose -f docker-compose.migration.yml exec django python manage.py migrate_legacy_data "$@"
        ;;

    "reset-test-data")
        if ! check_migration_env; then
            print_error "Migration environment is not running. Start it with: bash scripts/migration-env.sh start"
            exit 1
        fi

        print_status "🧪 Resetting test data..."
        docker compose -f docker-compose.migration.yml exec django python manage.py setup_test_data --clear-existing
        ;;

    "reset-migration-data")
        if ! check_migration_env; then
            print_error "Migration environment is not running. Start it with: bash scripts/migration-env.sh start"
            exit 1
        fi

        print_warning "This will clear all migration data!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "🧹 Clearing migration data..."
            docker compose -f docker-compose.migration.yml exec django python manage.py migrate_legacy_data --clear-existing --dry-run
            print_status "✅ Migration data cleared"
        fi
        ;;

    "backup")
        if ! check_migration_env; then
            print_error "Migration environment is not running. Start it with: bash scripts/migration-env.sh start"
            exit 1
        fi

        print_status "💾 Creating backup..."
        docker compose -f docker-compose.migration.yml exec postgres backup
        print_status "✅ Backup created"
        ;;

    "psql")
        if ! check_migration_env; then
            print_error "Migration environment is not running. Start it with: bash scripts/migration-env.sh start"
            exit 1
        fi

        shift
        database="${1:-naga_test}"
        print_status "🗄️  Connecting to database: $database"
        docker compose -f docker-compose.migration.yml exec postgres psql -U postgres -d "$database"
        ;;

    "test")
        if ! check_migration_env; then
            print_error "Migration environment is not running. Start it with: bash scripts/migration-env.sh start"
            exit 1
        fi

        print_status "🧪 Running tests in migration environment..."
        shift
        docker compose -f docker-compose.migration.yml exec django pytest "$@"
        ;;

    "help"|*)
        echo "Migration Environment Management"
        echo ""
        echo "Usage: bash scripts/migration-env.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start                Start migration environment"
        echo "  stop                 Stop migration environment"
        echo "  restart              Restart migration environment"
        echo "  status               Show environment status"
        echo "  logs [service]       Show logs (optional service filter)"
        echo "  shell                Access Django shell"
        echo "  migrate-legacy [opts] Import legacy data"
        echo "  reset-test-data      Reset test database with faker data"
        echo "  reset-migration-data Clear migration database"
        echo "  backup               Create database backup"
        echo "  psql [database]      Connect to PostgreSQL (default: naga_test)"
        echo "  test [pytest-args]   Run tests"
        echo "  help                 Show this help"
        echo ""
        echo "Examples:"
        echo "  bash scripts/migration-env.sh start"
        echo "  bash scripts/migration-env.sh migrate-legacy --data-type=students"
        echo "  bash scripts/migration-env.sh logs django"
        echo "  bash scripts/migration-env.sh psql naga_migration"
        ;;
esac
