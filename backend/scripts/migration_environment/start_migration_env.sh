#!/bin/bash
#
# MIGRATION ENVIRONMENT - Start and Setup Script
# This script starts the migration environment for legacy data import
#

set -e

echo "🔄 Starting MIGRATION Environment"
echo "=================================="

# Check if environment files exist
if [ ! -f ".envs/.migration/.django" ] || [ ! -f ".envs/.migration/.postgres" ]; then
    echo "⚠️ Creating missing migration environment files..."

    mkdir -p .envs/.migration

    # Create Django env file
    cat > .envs/.migration/.django << 'EOF'
# General
# ------------------------------------------------------------------------------
USE_DOCKER=yes
IPYTHONDIR=/app/.ipython

# Redis
# ------------------------------------------------------------------------------
REDIS_URL=redis://redis:6379/0

# Dramatiq
# ------------------------------------------------------------------------------
DRAMATIQ_BROKER_URL=redis://redis:6379/0

# Environment
# ------------------------------------------------------------------------------
DJANGO_SETTINGS_MODULE=config.settings.migration
EOF

    # Create Postgres env file
    cat > .envs/.migration/.postgres << 'EOF'
# PostgreSQL
# ------------------------------------------------------------------------------
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=naga_migration_v1
POSTGRES_USER=debug
POSTGRES_PASSWORD=debug
DATABASE_URL=postgresql://debug:debug@postgres:5432/naga_migration_v1
EOF

    echo "✅ Environment files created"
fi

# Start migration environment
echo "📦 Starting Docker containers..."
docker compose -f docker-compose.migration.yml up -d postgres redis mailpit

# Wait for postgres to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
docker compose -f docker-compose.migration.yml exec -T postgres sh -c 'until pg_isready -U $POSTGRES_USER -d $POSTGRES_DB; do sleep 1; done'

# Run migrations
echo "🔄 Running database migrations..."
docker compose -f docker-compose.migration.yml run --rm django python manage.py migrate

# Start Django services
echo "🚀 Starting Django services..."
docker compose -f docker-compose.migration.yml up -d

echo "✅ Migration environment is ready!"
echo ""
echo "🌐 Services:"
echo "  - Django: http://localhost:8001"
echo "  - Mailpit: http://localhost:8026"
echo ""
echo "🗄️ Database: naga_migration_v1"
echo "📁 Ready for legacy data import"
echo ""
echo "To stop: docker compose -f docker-compose.migration.yml down"
