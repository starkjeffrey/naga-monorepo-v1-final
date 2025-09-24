# OPUS Migration Squashing Instructions

**CRITICAL**: Follow these instructions EXACTLY in order. Each step has validation checks.

## ⚠️ CRITICAL WARNING: TEST DATABASE REQUIRED ⚠️

**DO NOT RUN THESE COMMANDS AGAINST THE LOCAL DATABASE (`naga_local`)!**

The original instructions had a MAJOR FLAW: they tested migrations against the production local database which contains existing data. This causes test failures because fixtures try to create records that already exist.

You MUST create and use a separate test database for migration squashing validation.

## Prerequisites Check

1. **Backup Production Database FIRST**:
```bash
# Create timestamped backup of your local database
docker compose -f docker-compose.local.yml exec postgres pg_dump -U debug naga_local | gzip > naga_local_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Verify backup
gzip -t naga_local_backup_*.sql.gz && echo "Backup is valid"
```

2. **Create Git Backup Branch**:
```bash
git checkout -b migration-squashing-backup
git add -A && git commit -m "🔧 BACKUP: Pre-migration squashing state" --no-verify
```

3. **Setup Test Database Environment**:
```bash
# Stop all containers
docker compose -f docker-compose.local.yml down

# Start PostgreSQL and Redis
docker compose -f docker-compose.local.yml up -d postgres redis
sleep 10

# Create a separate test database
docker compose -f docker-compose.local.yml exec postgres psql -U debug -d naga_local -c "DROP DATABASE IF EXISTS naga_squash_test;"
docker compose -f docker-compose.local.yml exec postgres psql -U debug -d naga_local -c "CREATE DATABASE naga_squash_test;"
```

4. **Create Migration State Snapshot**:
```bash
docker compose -f docker-compose.local.yml run --rm django python manage.py showmigrations > migration_state_before.txt
```

## CRITICAL: Test Database Configuration

**For ALL testing commands, you MUST use one of these SAFE approaches:**

### Option A: Dedicated PostgreSQL Test Environment (RECOMMENDED)
```bash
# Start test PostgreSQL environment (completely separate from local)
docker compose -f docker-compose.test-postgres.yml up -d

# Apply migrations to fresh test database
docker compose -f docker-compose.test-postgres.yml run --rm django python manage.py migrate

# Run tests
docker compose -f docker-compose.test-postgres.yml run --rm django pytest apps/APPNAME/tests/ -v

# Clean up when done
docker compose -f docker-compose.test-postgres.yml down
```

### Option B: SQLite Test Environment (FASTEST)
```bash
# Start SQLite test environment (no PostgreSQL needed)
docker compose -f docker-compose.test-sqlite.yml up -d

# Apply migrations to SQLite
docker compose -f docker-compose.test-sqlite.yml run --rm django python manage.py migrate

# Run tests
docker compose -f docker-compose.test-sqlite.yml run --rm django pytest apps/APPNAME/tests/ -v

# Clean up when done
docker compose -f docker-compose.test-sqlite.yml down
```

### Option C: Direct SQLite (NO DOCKER - FASTEST)
```bash
# Use SQLite directly with uv (fastest option)
DJANGO_SETTINGS_MODULE=config.settings.test_sqlite uv run pytest apps/APPNAME/tests/ -v
```

## NEW Test Environment Details

### PostgreSQL Test Environment
- **Database**: `naga_test_migrations` (completely separate)
- **Credentials**: `testuser/testpass123` (different from local)
- **Port**: 5434 (different from local 5432)
- **Container**: `naga_test_postgres`

### SQLite Test Environment  
- **Database**: `/app/test_data/test_migrations.sqlite3` (file-based)
- **No credentials needed**
- **No port conflicts**
- **Container**: `naga_test_sqlite_django`

## Phase 1: Simple Apps (Safe Testing)

### ACTUAL Migration Counts (as of 2024-08-24):
- **mobile**: 1 migration (cannot squash - skip)
- **moodle**: 0 migrations (no migrations - skip)
- **language**: 2 migrations (can squash)
- **attendance**: 3 migrations (already has squashed migration)

### Step 1: language app (2 migrations → 1)
```bash
# Check current migrations
ls apps/language/migrations/ | grep -E "^[0-9]{4}_"
# Should show: 0001_initial.py, 0002_initial.py

# Squash migrations
docker compose -f docker-compose.local.yml run --rm django python manage.py squashmigrations language 0001 0002 --no-input

# Test with Option A (Dedicated PostgreSQL test environment)
docker compose -f docker-compose.test-postgres.yml up -d
docker compose -f docker-compose.test-postgres.yml run --rm django python manage.py migrate
docker compose -f docker-compose.test-postgres.yml run --rm django pytest apps/language/tests/ -v
docker compose -f docker-compose.test-postgres.yml down

# OR Test with Option C (Direct SQLite - fastest)
DJANGO_SETTINGS_MODULE=config.settings.test_sqlite uv run pytest apps/language/tests/ -v

# ✅ SUCCESS CHECK: If tests pass, continue. If tests fail, STOP and revert.
```

### Step 2: attendance app (if not already squashed)
```bash
# Check if already squashed
ls apps/attendance/migrations/ | grep squashed
# If already has squashed migration, skip to next app

# If not squashed, squash migrations
docker compose -f docker-compose.local.yml run --rm django python manage.py squashmigrations attendance 0001 0002 --no-input

# Test with pytest
docker compose -f docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django pytest apps/attendance/tests/ --create-db -v

# ✅ SUCCESS CHECK: Tests must pass to continue
```

## Phase 2: Medium Apps (Moderate Risk)

**ONLY proceed if Phase 1 completed successfully.**

### ACTUAL Migration Counts (as of 2024-08-24):
1. **accounts** (3 migrations)
2. **grading** (4 migrations)  
3. **common** (6 migrations) - ⚠️ CRITICAL APP - test thoroughly
4. **people** (11 migrations) - ⚠️ HIGH RISK - extensive testing required

### Template for each app:
```bash
# Replace APP_NAME with actual app name
export APP_NAME="accounts"  # or grading, common, people

# 1. Check migration count
ls apps/$APP_NAME/migrations/

# 2. Find last migration number
LAST_MIGRATION=$(ls apps/$APP_NAME/migrations/*.py | grep -E "[0-9]{4}_" | sort | tail -1 | grep -o "[0-9]{4}")
echo "Last migration: $LAST_MIGRATION"

# 3. Squash migrations  
docker compose -f docker-compose.local.yml run --rm django python manage.py squashmigrations $APP_NAME 0001 $LAST_MIGRATION --no-input

# 4. Test fresh migration
docker compose -f docker-compose.local.yml down
docker compose -f docker-compose.local.yml up -d postgres redis
sleep 10
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate --run-syncdb

# 5. Run comprehensive tests
docker compose -f docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django python manage.py test apps.$APP_NAME -v 2

# 6. ✅ VALIDATION: Must pass ALL tests before proceeding to next app
# 7. If ANY test fails, STOP immediately and document the failure
```

### Special Instructions for Critical Apps:

**common app** - Foundation layer, affects all other apps:
```bash
# Additional validation after squashing common
docker compose -f docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django python manage.py test apps.people apps.curriculum -v 2
# Must test dependent apps to ensure common changes didn't break them
```

**people app** - Core domain, affects most other apps:
```bash
# Extended validation after squashing people
docker compose -f docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django python manage.py test apps.enrollment apps.academic apps.attendance -v 2
# Test all apps that depend on people models
```

## Phase 3: High Risk Apps (PROCEED WITH EXTREME CAUTION)

**⚠️ WARNING**: These apps have complex dependencies. Only attempt if Phases 1-2 completed flawlessly.

### ACTUAL Migration Counts (as of 2024-08-24):
1. **curriculum** (14 migrations) - Core domain
2. **scheduling** (15 migrations) - Depends on curriculum  
3. **enrollment** (22 migrations) - Depends on people, curriculum, scheduling
4. **finance** (38 migrations) - Most complex, many field conflicts
5. **academic** (9 migrations) - Known conflicts, handle last

### Template for High Risk Apps:
```bash
export APP_NAME="curriculum"  # Update for each app

# 1. Create app-specific backup branch
git checkout -b backup-$APP_NAME-migrations
git add -A && git commit -m "🔧 BACKUP: Pre-$APP_NAME squashing"

# 2. Detailed dependency check
echo "=== Checking dependencies for $APP_NAME ==="
grep -r "apps\.$APP_NAME" apps/*/models.py
grep -r "$APP_NAME\." apps/*/migrations/

# 3. Squash with extra validation
LAST_MIGRATION=$(ls apps/$APP_NAME/migrations/*.py | grep -E "[0-9]{4}_" | sort | tail -1 | grep -o "[0-9]{4}")
echo "Squashing $APP_NAME migrations 0001 to $LAST_MIGRATION"

docker compose -f docker-compose.local.yml run --rm django python manage.py squashmigrations $APP_NAME 0001 $LAST_MIGRATION --no-input

# 4. Test with dependency apps
docker compose -f docker-compose.local.yml down && docker compose -f docker-compose.local.yml up -d postgres redis
sleep 10
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate --run-syncdb

# 5. Comprehensive testing
docker compose -f docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django python manage.py test apps.$APP_NAME -v 2

# 6. Test dependent apps (critical for high-risk apps)
case $APP_NAME in
  curriculum)
    docker compose -f docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django python manage.py test apps.scheduling apps.enrollment -v 2
    ;;
  scheduling) 
    docker compose -f docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django python manage.py test apps.enrollment -v 2
    ;;
  enrollment)
    docker compose -f docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django python manage.py test apps.academic apps.attendance -v 2
    ;;
  finance)
    echo "Finance squashing complete - test all payment workflows manually"
    ;;
esac

# 7. ✅ SUCCESS CRITERIA: ALL tests pass + dependent app tests pass
# 8. ❌ FAILURE PROTOCOL: If ANY test fails, restore from backup branch immediately
```

## Error Recovery Protocol

If ANY step fails:

```bash
# 1. Document the failure
echo "Migration squashing failed at: [APP_NAME] [STEP_DESCRIPTION]" >> migration_failures.log
echo "Error details: [COPY_FULL_ERROR_OUTPUT]" >> migration_failures.log

# 2. Restore from backup
git checkout migration-squashing-backup
git branch -D backup-[FAILED_APP]-migrations  # Clean up failed branch

# 3. Restart containers
docker compose -f docker-compose.local.yml down
docker compose -f docker-compose.local.yml up -d postgres redis
sleep 10

# 4. Verify restoration
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate --run-syncdb
docker compose -f docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django python manage.py test

# 5. Report failure with detailed context
```

## Final Validation

After ALL successful squashing:

```bash
# 1. Full system test
docker compose -f docker-compose.local.yml down
docker compose -f docker-compose.local.yml up -d postgres redis
sleep 10
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate --run-syncdb

# 2. Comprehensive test suite
docker compose -f docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django python manage.py test -v 2

# 3. SQLite compatibility test  
DJANGO_SETTINGS_MODULE=config.settings.test_sqlite uv run pytest apps/ -v

# 4. Create final state snapshot
docker compose -f docker-compose.local.yml run --rm django python manage.py showmigrations > migration_state_after.txt

# 5. Generate success report
echo "=== MIGRATION SQUASHING COMPLETE ===" >> migration_success.log
echo "Apps successfully squashed:" >> migration_success.log
ls apps/*/migrations/*squashed*.py >> migration_success.log
```

## Success Criteria

✅ **Complete success only if:**
- All apps' tests pass individually
- All dependent apps' tests pass  
- Full system test suite passes
- SQLite compatibility maintained
- No migration conflicts in fresh database creation

❌ **Partial success handling:**
- Document which apps succeeded
- Keep successful squashed migrations
- Restore failed apps to original migration state
- Update SQLITE_TESTING_GUIDE.md with results

## Critical Safety Notes

1. **NEVER skip validation steps** - each test failure indicates dependency breaks
2. **NEVER proceed to high-risk apps if medium-risk apps fail**  
3. **ALWAYS maintain backup branches** for each critical app
4. **STOP IMMEDIATELY** if you see field reference errors like "field 'xyz' doesn't exist"
5. **Test dependent apps** - squashing one app can break apps that depend on it

This process should take 4-8 hours for careful execution with full validation.