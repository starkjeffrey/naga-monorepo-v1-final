# Foundation Data Fixtures

System-wide reference data that other fixtures depend on. Load these first.

## Files:

- `cambodian_holidays.json` - National holidays for Cambodia (2025-2026)
- `cambodian_provinces.json` - Province/location reference data
- `system_settings.json` - System configuration settings
- `currencies.json` - Currency reference data

## Loading:

```bash
python manage.py loaddata apps/common/fixtures/01_foundation/*.json
```

This data must be loaded before any other fixtures that reference locations, holidays, or system settings.
