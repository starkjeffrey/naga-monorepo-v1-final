# People and Users Fixtures

Core people data and user accounts. Depends on foundation data.

## Files:

- `sample_users.json` - Development user accounts (admin, staff, teachers)
- `sample_people.json` - Sample person records with demographics
- `sample_students.json` - Student profiles with various statuses
- `sample_teachers.json` - Teacher profiles with employment data

## Dependencies:

- Requires `01_foundation/` to be loaded first
- Province data needed for birth_province fields

## Loading:

```bash
python manage.py loaddata apps/common/fixtures/02_people/*.json
```
