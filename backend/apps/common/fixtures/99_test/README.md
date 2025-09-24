# Test and Development Data Fixtures

Complete development environment and testing data. Includes comprehensive seed data for development.

## Files:

- `development_seed.json` - Complete development environment seed data
- `test_minimal.json` - Minimal test data for unit tests
- `test_comprehensive.json` - Full test scenario data

## Purpose:

- **Development**: Complete realistic data for development work
- **Testing**: Controlled test data for automated tests
- **Demos**: Sample data for demonstrations

## Dependencies:

- Requires all previous fixture directories to be loaded first
- Contains data that references foundation, people, curriculum, and business data

## Loading:

```bash
# Development environment
python manage.py loaddata apps/common/fixtures/99_test/development_seed.json

# Unit testing
python manage.py loaddata apps/common/fixtures/99_test/test_minimal.json
```

## Note:

Only load test fixtures in development and testing environments, never in production.
