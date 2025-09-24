from django.core.management.base import BaseCommand

from apps.curriculum.models import Course, Cycle


class Command(BaseCommand):
    help = "Fix invalid course cycle assignments"

    def handle(self, *args, **options):
        # Fix invalid cycles
        # LANGUAGE should be LANG
        language_fixed = Course.objects.filter(cycle="LANGUAGE").update(cycle="LANG")
        self.stdout.write(f"Fixed {language_fixed} courses from LANGUAGE to LANG cycle")

        # MA should be MASTERS
        ma_fixed = Course.objects.filter(cycle="MA").update(cycle="MASTERS")
        self.stdout.write(f"Fixed {ma_fixed} courses from MA to MASTERS cycle")

        # Verify all courses now have valid cycles
        self.stdout.write("\nVerifying all courses have valid cycles:")
        invalid_cycles = []
        mismatched = []

        for course in Course.objects.filter(is_active=True):
            try:
                cycle_obj = Cycle.objects.get(short_name=course.cycle)
                # Check if division matches
                if course.division != cycle_obj.division:
                    mismatched.append(course)
                    self.stdout.write(
                        f"MISMATCH: {course.code} in {course.division.short_name} division "
                        f"but {course.cycle} cycle belongs to {cycle_obj.division.short_name}"
                    )
            except Cycle.DoesNotExist:
                invalid_cycles.append(course)
                self.stdout.write(f"INVALID: {course.code} has invalid cycle: {course.cycle}")

        self.stdout.write(f"\nRemaining invalid cycles: {len(invalid_cycles)}")
        self.stdout.write(f"Division-cycle mismatches: {len(mismatched)}")

        if mismatched:
            self.stdout.write("\nTo fix mismatches, courses should be moved to appropriate cycles in their divisions.")
            for course in mismatched[:5]:  # Show first 5 as examples
                cycle_obj = Cycle.objects.get(short_name=course.cycle)
                self.stdout.write(
                    f"  {course.code}: Move to {course.division.name} or change to {cycle_obj.division.name}",
                )
