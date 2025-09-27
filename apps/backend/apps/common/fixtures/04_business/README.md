# Business Logic and Operations Fixtures

Sponsors, scholarships, finance data, and business operations. Depends on curriculum and people data.

## Files:

- `sponsors.json` - Standard sponsor organization data
- `sample_scholarships.json` - Sample scholarship records
- `sample_finance.json` - Sample financial/pricing data

## Dependencies:

- Requires `01_foundation/`, `02_people/`, and `03_curriculum/` to be loaded first
- Scholarships reference student profiles
- Sponsors may reference contact information

## Loading:

```bash
python manage.py loaddata apps/common/fixtures/04_business/*.json
```

## Notes:

- Sponsor data contains standard partner organizations
- All files are safe for both production and development use
