# Program Transition System Usage Guide

## Overview

The new ProgramTransition model tracks each distinct period a student spends in a program, capturing:
- Language program transitions (IEAP → GESL → EHSS)
- Progression from language to BA
- BA to MA transitions
- Any returns or gaps in enrollment

## Key Features

1. **One record per program period** - If a student does IEAP for 2 terms, then BA for 8 terms, they'll have 2 transition records
2. **Tracks duration** - Each period shows days/months/years spent
3. **Academic performance** - Credits earned, GPA for each period
4. **Completion status** - Whether they completed, graduated, or dropped from each program

## Running the Migration

1. First, run the database migration to create the new model:
```bash
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate enrollment
```

2. Then populate the transition records:
```bash
# For a specific student (like 10774)
docker compose -f docker-compose.local.yml run --rm django python manage.py create_program_transitions --student-id 10774

# For all students
docker compose -f docker-compose.local.yml run --rm django python manage.py create_program_transitions

# Dry run to see what would be created
docker compose -f docker-compose.local.yml run --rm django python manage.py create_program_transitions --student-id 10774 --dry-run
```

## Viewing in Admin

After running the migration, you can view transitions in Django admin at:
`/admin/enrollment/programtransition/`

Filter by student ID 10774 to see their complete journey.

## Example Output

For student 10774, you should see something like:
1. IEAP (2 terms, completed level 4)
2. BA in [Major] (8+ terms, 120+ credits, graduated)

## Fixing the Original Issue

The original `_determine_journey_status` method needs updating to check these transitions:

```python
def _determine_journey_status(self, phases: list[dict], enrollments: list[ClassHeaderEnrollment]) -> str:
    """Determine overall journey status based on transitions."""
    # Check if student has any GRADUATED transitions
    if hasattr(self, 'transitions'):
        graduated_transitions = self.transitions.filter(
            completion_status='GRADUATED'
        ).exists()
        if graduated_transitions:
            return AcademicJourney.JourneyStatus.GRADUATED
    
    # Rest of the logic...
```

## Next Steps

1. Run the migration and transition creation for student 10774
2. Verify the transitions look correct in admin
3. Update the journey status logic to use these transitions
4. Create a comprehensive view/report showing full academic paths