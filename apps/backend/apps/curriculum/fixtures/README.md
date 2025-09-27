# Curriculum Fixtures

This directory contains fixture data for all curriculum models.

## Files

- `divisions.json` - Academic divisions (Language Division, etc.)
- `cycles.json` - Academic cycles (undergraduate, graduate, etc.)
- `majors.json` - Academic majors/programs
- `terms.json` - Academic terms/periods
- `courses.json` - Course catalog data

## Data Counts

- Divisions: 2 records
- Cycles: 3 records
- Majors: 15 records
- Terms: 177 records
- Courses: 205 records

## Loading Data

To load all curriculum data:

```bash
# Load in dependency order
python manage.py loaddata divisions cycles majors terms courses

# Or load specific model
python manage.py loaddata curriculum/fixtures/courses.json
```

## Regenerating Fixtures

To create fresh fixtures from current database:

```bash
python manage.py dumpdata curriculum.Division --format=json --indent=2 > apps/curriculum/fixtures/divisions.json
python manage.py dumpdata curriculum.Cycle --format=json --indent=2 > apps/curriculum/fixtures/cycles.json
python manage.py dumpdata curriculum.Major --format=json --indent=2 > apps/curriculum/fixtures/majors.json
python manage.py dumpdata curriculum.Term --format=json --indent=2 > apps/curriculum/fixtures/terms.json
python manage.py dumpdata curriculum.Course --format=json --indent=2 > apps/curriculum/fixtures/courses.json
```

Last updated: $(date)
