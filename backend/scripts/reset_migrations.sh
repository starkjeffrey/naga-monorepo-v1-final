#!/bin/bash

echo "🚨 MIGRATION RESET STARTING..."

# 1. Mark all migrations as unapplied (fake reverse)
apps=(academic_records academic accounts attendance common curriculum enrollment finance grading language level_testing mobile people scheduling scholarships web_interface)
for app in "${apps[@]}"; do
    echo "Fake reversing $app migrations..."
    docker compose -f docker-compose.local.yml run --rm django \
        python manage.py migrate $app zero --fake
done

# 2. Remove migration files (keep __init__.py)
for app in "${apps[@]}"; do
    echo "Removing migration files for $app..."
    find apps/$app/migrations -name "*.py" -not -name "__init__.py" -delete
    find apps/$app/migrations -name "*.pyc" -delete
done

# 3. Create fresh initial migrations
for app in "${apps[@]}"; do
    echo "Creating initial migration for $app..."
    docker compose -f docker-compose.local.yml run --rm django \
        python manage.py makemigrations $app --name initial
done

# 4. Fake apply all migrations (database already has the schema)
for app in "${apps[@]}"; do
    echo "Fake applying $app migrations..."
    docker compose -f docker-compose.local.yml run --rm django \
        python manage.py migrate $app --fake
done

echo "✅ MIGRATION RESET COMPLETE"