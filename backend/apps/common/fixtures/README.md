# Django Fixtures for Naga SIS V1.0

This directory contains Django fixtures organized by dependency order and data type for the Naga Student Information System v1.0.

## Organized Fixture Structure

Fixtures are organized in numbered directories to ensure proper loading order:

### 01_foundation/ - Foundation Data

System-wide reference data that other apps depend on:

- `cambodian_holidays.json` - National holidays for Cambodia
- `cambodian_provinces.json` - Province/location reference data
- `system_settings.json` - System configuration settings
- `currencies.json` - Currency reference data

### 02_people/ - People and Users

Core people data and user accounts:

- `sample_users.json` - Development user accounts
- `sample_people.json` - Sample person records
- `sample_students.json` - Sample student profiles
- `sample_teachers.json` - Sample teacher profiles

### 03_curriculum/ - Academic Structure

Academic programs, courses, and terms:

- `sample_terms.json` - Academic terms/semesters
- `sample_programs.json` - Academic programs
- `sample_courses.json` - Course catalog
- `sample_textbooks.json` - Textbook library

### 04_business/ - Business Logic

Sponsors, scholarships, and business operations:

- `sponsors_production.json` - Production sponsor data
- `sponsors_v1_fixed.json` - Fixed sponsor data for development
- `sample_scholarships.json` - Sample scholarship data
- `sample_finance.json` - Sample financial data

### 99_test/ - Test Data

Development and testing fixtures:

- `development_seed.json` - Complete development environment seed data
- `test_minimal.json` - Minimal test data for unit tests

## Loading Order

Load fixtures in dependency order using the numbered directories:

```bash
# Load foundation data first
python manage.py loaddata apps/common/fixtures/01_foundation/*.json

# Load people data
python manage.py loaddata apps/common/fixtures/02_people/*.json

# Load curriculum data
python manage.py loaddata apps/common/fixtures/03_curriculum/*.json

# Load business data
python manage.py loaddata apps/common/fixtures/04_business/*.json

# Load test data (development only)
python manage.py loaddata apps/common/fixtures/99_test/*.json
```

Or use Docker:

```bash
# Load all foundation fixtures
docker compose -f docker-compose.local.yml run --rm django \
  python manage.py loaddata apps/common/fixtures/01_foundation/*.json

# Load complete development environment
docker compose -f docker-compose.local.yml run --rm django \
  python manage.py loaddata \
  apps/common/fixtures/01_foundation/*.json \
  apps/common/fixtures/02_people/*.json \
  apps/common/fixtures/03_curriculum/*.json \
  apps/common/fixtures/04_business/*.json
```

## Production vs Development

- **Production fixtures**: Use only `01_foundation/` and `04_business/sponsors_production.json`
- **Development fixtures**: Use all directories including `99_test/`
- **Testing fixtures**: Use minimal data from `99_test/test_minimal.json`

## Data Sources

Fixtures are migrated and adapted from:

- Original V0 system: `/Users/jeffreystark/PycharmProjects/naga-backend_version_0/`
- Production data exports from legacy system
- Manually created development seed data

## Notes

- All fixtures use proper app.model naming (e.g., `scholarships.sponsor`)
- Primary keys preserved where possible for data consistency
- Foreign key relationships maintained through proper loading order
- Date fields use ISO format (YYYY-MM-DD)
- All fixtures follow V1.0 model structure and clean architecture
- Fixtures are safe for repeated loading (idempotent where possible)

## AuditModel Requirements

⚠️ **CRITICAL**: All models inheriting from `AuditModel` require these fields in fixtures:

```json
{
  "model": "app.model",
  "pk": 1,
  "fields": {
    "name": "Example",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z",
    "is_deleted": false,
    "deleted_at": null
  }
}
```

Models inheriting from `AuditModel` include:

- `curriculum.Division`, `curriculum.Cycle`, `curriculum.Major`
- `curriculum.Course`, `curriculum.Term`, `curriculum.Textbook`
- `common.Room`, `scholarships.Sponsor`
- All other models extending `AuditModel`

**Loading will fail** without these fields due to NOT NULL constraints.

## Clean Architecture Compliance

This fixture organization supports the Naga SIS v1.0 clean architecture by:

- **Dependency Management**: Numbered directories enforce proper dependency order
- **Single Responsibility**: Each directory contains related data only
- **Clean Dependencies**: Foundation data loads before dependent data
- **Separation of Concerns**: Production vs development vs test data clearly separated
