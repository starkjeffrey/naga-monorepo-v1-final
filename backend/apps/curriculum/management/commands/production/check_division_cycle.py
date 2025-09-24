from django.core.management.base import BaseCommand

from apps.curriculum.models import Course, Cycle


class Command(BaseCommand):
    help = "Check for division-cycle mismatches in courses"

    def handle(self, *args, **options):
        # Check current cycle-division relationships
        self.stdout.write("Current Cycle-Division relationships:")
        for cycle in Cycle.objects.all():
            self.stdout.write(f"  {cycle.short_name} cycle belongs to {cycle.division.name}")

        self.stdout.write("\nCourses with mismatched division-cycle:")
        mismatched = []
        for course in Course.objects.filter(is_active=True):
            # Get the cycle object based on the course's cycle string
            try:
                cycle_obj = Cycle.objects.get(short_name=course.cycle)
                if course.division != cycle_obj.division:
                    mismatched.append(course)
                    self.stdout.write(
                        f"  {course.code}: Division={course.division.short_name}, "
                        f"Cycle={course.cycle} (cycle belongs to {cycle_obj.division.short_name})"
                    )
            except Cycle.DoesNotExist:
                self.stdout.write(f'  {course.code}: Invalid cycle "{course.cycle}"')

        self.stdout.write(f"\nTotal mismatched courses: {len(mismatched)}")

        if mismatched:
            self.stdout.write(
                "\nWould you like to fix these mismatches? "
                "This will update the course cycles to match their divisions."
            )
