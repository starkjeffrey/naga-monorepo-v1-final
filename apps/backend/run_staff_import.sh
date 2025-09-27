#!/bin/bash

# Run staff import with Docker for LOCAL environment
echo "Running staff import in DRY RUN mode..."
docker compose -f docker-compose.local.yml run --rm django python manage.py import_staff data/migrate/staff.csv --dry-run

echo ""
echo "If the above looks correct, run the following command to actually import:"
echo "docker compose -f docker-compose.local.yml run --rm django python manage.py import_staff data/migrate/staff.csv"