# Academic Journey Status Logic Fix

## Current Problems

1. **Incorrect "DROPPED" Status**: Students who completed programs are marked as DROPPED if their last enrollment was >24 months ago
2. **No Program Transition Recognition**: System doesn't recognize when students complete one program (e.g., IEAP) and transition to another (e.g., BA)
3. **Graduation Not Detected**: Even students with 43 completed courses and high GPAs are marked as dropped

## Where to Fix

### 1. Fix the Journey Status Logic (`progression_builder.py`, lines 617-640)

The `_determine_journey_status` method needs to be rewritten to:
- Check for actual program completions first
- Only mark as DROPPED if they left without completing any program
- Add proper status like GRADUATED

### 2. Fix Language Program Completion Status (`progression_builder.py`, lines 683-685)

Instead of defaulting to "DROPPED", add logic to detect:
- COMPLETED: Finished the program (e.g., IEAP-4)
- TRANSITIONED: Completed and moved to BA
- ACTIVE: Still in progress
- DROPPED: Actually dropped out

### 3. Add Graduation Detection

The system needs to detect graduation based on:
- Credit requirements met (typically 120+ for BA)
- High number of completed courses
- Completion patterns

## Implementation Steps

1. **Create a new management command** to fix existing journey statuses
2. **Update the progression builder** to have better status detection
3. **Add data validation** to catch these issues earlier

## Example Fix for `_determine_journey_status`:

```python
def _determine_journey_status(self, phases: list[dict], enrollments: list[ClassHeaderEnrollment]) -> str:
    """Determine overall journey status with proper graduation detection."""
    if not phases:
        return AcademicJourney.JourneyStatus.UNKNOWN
    
    # Check for graduations
    has_ba_graduation = any(
        p["type"] == "bachelor" and 
        (p.get("completion_status") == "completed" or 
         self._check_ba_completion(p.get("enrollments", [])))
        for p in phases
    )
    has_ma_graduation = any(
        p["type"] == "master" and 
        p.get("completion_status") == "completed" 
        for p in phases
    )
    
    # If graduated, return GRADUATED regardless of time
    if has_ma_graduation or has_ba_graduation:
        return AcademicJourney.JourneyStatus.GRADUATED
    
    # Check last enrollment date
    last_enrollment_date = enrollments[-1].class_header.term.end_date
    months_since_last = (date.today() - last_enrollment_date).days / 30
    
    # Only mark as DROPPED if they didn't complete any program
    completed_language = any(
        p["type"] == "language" and 
        p.get("completion_status") == "completed" 
        for p in phases
    )
    
    if months_since_last < 6:
        return AcademicJourney.JourneyStatus.ACTIVE
    elif months_since_last < 24:
        return AcademicJourney.JourneyStatus.INACTIVE
    elif completed_language:
        # They completed language but haven't enrolled recently
        # Likely graduated or transferred
        return AcademicJourney.JourneyStatus.GRADUATED
    else:
        return AcademicJourney.JourneyStatus.DROPPED

def _check_ba_completion(self, enrollments: list[ClassHeaderEnrollment]) -> bool:
    """Check if BA requirements are likely met."""
    if not enrollments:
        return False
    
    # Count completed credits
    completed_credits = 0
    for e in enrollments:
        if e.final_grade in self.PASSING_GRADES:
            completed_credits += float(e.class_header.course.credits or 0)
    
    # BA typically requires 120+ credits
    return completed_credits >= 120
```

## Quick Fix Script

Create a management command to fix existing records:

```python
# apps/enrollment/management/commands/fix_journey_statuses.py
from django.core.management.base import BaseCommand
from apps.enrollment.models_progression import AcademicJourney
from apps.enrollment.models import ClassHeaderEnrollment

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Fix students marked as DROPPED who actually graduated
        for journey in AcademicJourney.objects.filter(journey_status='DROPPED'):
            enrollments = ClassHeaderEnrollment.objects.filter(
                student=journey.student
            ).select_related('class_header__course')
            
            # Count completed credits
            completed_credits = 0
            completed_courses = 0
            
            for e in enrollments:
                if e.final_grade in ['A', 'B', 'C', 'D', 'CR']:
                    completed_credits += float(e.class_header.course.credits or 0)
                    completed_courses += 1
            
            # If they have 120+ credits or 40+ courses, they likely graduated
            if completed_credits >= 120 or completed_courses >= 40:
                journey.journey_status = AcademicJourney.JourneyStatus.GRADUATED
                journey.add_data_issue("Status corrected from DROPPED to GRADUATED")
                journey.save()
                self.stdout.write(
                    f"Fixed {journey.student.student_id}: "
                    f"{completed_courses} courses, {completed_credits} credits"
                )
```