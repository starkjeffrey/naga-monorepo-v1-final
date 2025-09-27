#!/bin/bash
# Migrate both test and migration databases
# Usage: ./scripts/migrate-both.sh [app_name]

echo "🔄 Running migrations on both databases..."

# Migration database (with real data)
echo "📊 Migrating MIGRATION database..."
docker compose -f docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.migration django python manage.py migrate $1

if [ $? -eq 0 ]; then
    echo "✅ Migration database updated successfully"
else
    echo "❌ Migration database failed - stopping"
    exit 1
fi

# Default/test database
echo "🧪 Migrating DEFAULT database..."
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate $1

if [ $? -eq 0 ]; then
    echo "✅ Default database updated successfully"
    echo "🎉 Both databases are now in sync!"
else
    echo "❌ Default database failed"
    exit 1
fi
