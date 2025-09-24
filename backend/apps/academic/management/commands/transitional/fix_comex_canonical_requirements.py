"""Management command to fix COMEX-488 canonical requirement data integrity issues.

This command addresses the critical architectural issue where COMEX-488 was incorrectly
set as a direct canonical requirement in multiple majors. The correct model is:

- COMEX-488 should NEVER be a direct canonical requirement
- COMEX-488 should fulfill senior project requirements via course equivalencies only
- Each major's senior project course should have a unidirectional equivalency with COMEX-488

Business Rule: Students can take EITHER their major's senior project OR COMEX-488 exit exam.
"""

from typing import Any

from django.db import models, transaction
from django.utils import timezone

from apps.academic.models import CanonicalRequirement, CourseEquivalency
from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Course, Term


class Command(BaseMigrationCommand):
    """Fix COMEX-488 canonical requirement data integrity issues."""

    help = "Remove incorrect COMEX-488 direct requirements and ensure proper equivalencies"

    def get_migration_name(self) -> str:
        """Return migration name for audit purposes."""
        return "fix_comex_canonical_requirements"

    def get_rejection_categories(self) -> list[str]:
        """Return list of possible rejection categories."""
        return [
            "MISSING_COURSE",
            "MISSING_MAJOR",
            "MISSING_TERM",
            "EQUIVALENCY_EXISTS",
            "CANONICAL_NOT_FOUND",
            "DATABASE_ERROR",
        ]

    def execute_migration(self, *args, **options) -> dict[str, Any]:
        """Execute the migration and return results."""
        return self.handle_migration(*args, **options)

    def handle_migration(self, *args, **options) -> dict[str, Any]:
        """Main migration logic."""
        results = {
            "comex_requirements_removed": 0,
            "equivalencies_fixed": 0,
            "equivalencies_created": 0,
            "students_affected": 0,
            "details": [],
        }

        # Step 1: Find and remove incorrect COMEX-488 canonical requirements
        self.stdout.write("Step 1: Removing incorrect COMEX-488 canonical requirements...")
        results.update(self._remove_comex_requirements())

        # Step 2: Fix existing bidirectional equivalencies to be unidirectional
        self.stdout.write("Step 2: Fixing existing bidirectional COMEX-488 equivalencies...")
        results.update(self._fix_existing_equivalencies())

        # Step 3: Create missing senior project equivalencies
        self.stdout.write("Step 3: Creating missing COMEX-488 equivalencies...")
        results.update(self._create_missing_equivalencies())

        # Step 4: Analyze impact on existing fulfillments
        self.stdout.write("Step 4: Analyzing impact on student fulfillments...")
        results.update(self._analyze_fulfillment_impact())

        return results

    @transaction.atomic
    def _remove_comex_requirements(self) -> dict[str, Any]:
        """Remove incorrect COMEX-488 canonical requirements."""
        try:
            comex_course = Course.objects.get(code="COMEX-488")
        except Course.DoesNotExist:
            self.record_rejection("MISSING_COURSE", "COMEX-488", "COMEX-488 course not found in database")
            return {"comex_requirements_removed": 0}

        # Find all COMEX-488 canonical requirements
        comex_requirements = CanonicalRequirement.objects.filter(
            required_course=comex_course, is_active=True
        ).select_related("major")

        removed_count = 0
        details = []

        for req in comex_requirements:
            # Record the requirement before deletion
            detail = {
                "canonical_req_id": req.id,
                "major_code": req.major.code,
                "major_name": req.major.name,
                "sequence_number": req.sequence_number,
                "requirement_name": req.name,
            }
            details.append(detail)

            self.stdout.write(
                f"  Removing COMEX-488 requirement from {req.major.code} (sequence {req.sequence_number})"
            )

            # Deactivate instead of delete to preserve audit trail
            req.is_active = False
            req.notes = (
                (req.notes or "") + f"\n[{timezone.now().date()}] Deactivated: COMEX-488 should only fulfill "
                "requirements via equivalency, not as direct requirement."
            )
            req.save()

            removed_count += 1

        self.record_success("comex_requirements_removed", removed_count)
        self.record_sample_data("removed_requirements", details)

        return {"comex_requirements_removed": removed_count, "removal_details": details}

    @transaction.atomic
    def _fix_existing_equivalencies(self) -> dict[str, Any]:
        """Fix existing bidirectional COMEX-488 equivalencies to be unidirectional."""
        try:
            comex_course = Course.objects.get(code="COMEX-488")
        except Course.DoesNotExist:
            self.record_rejection("MISSING_COURSE", "COMEX-488", "COMEX-488 course not found in database")
            return {"equivalencies_fixed": 0}

        # Find existing COMEX-488 equivalencies that are bidirectional
        bidirectional_equivalencies = CourseEquivalency.objects.filter(
            models.Q(original_course=comex_course) | models.Q(equivalent_course=comex_course),
            bidirectional=True,
            is_active=True,
        ).select_related("original_course", "equivalent_course")

        fixed_count = 0
        details = []

        for equiv in bidirectional_equivalencies:
            # Determine correct orientation: senior project → COMEX-488
            if equiv.original_course.code == "COMEX-488":
                # Wrong orientation, need to flip
                original_course = equiv.equivalent_course
                equivalent_course = equiv.original_course
            else:
                # Correct orientation
                original_course = equiv.original_course
                equivalent_course = equiv.equivalent_course

            detail = {
                "equivalency_id": equiv.id,
                "original_course_before": equiv.original_course.code,
                "equivalent_course_before": equiv.equivalent_course.code,
                "bidirectional_before": True,
                "original_course_after": original_course.code,
                "equivalent_course_after": equivalent_course.code,
                "bidirectional_after": False,
            }
            details.append(detail)

            self.stdout.write(
                f"  Fixing equivalency: {equiv.original_course.code} ↔ {equiv.equivalent_course.code} "
                f"→ {original_course.code} → {equivalent_course.code}"
            )

            # Update the equivalency
            equiv.original_course = original_course
            equiv.equivalent_course = equivalent_course
            equiv.bidirectional = False
            equiv.reason = (
                f"COMEX-488 (exit exam) can substitute for {original_course.code} "
                "(senior project) to fulfill graduation requirement"
            )
            equiv.save()

            fixed_count += 1

        self.record_success("equivalencies_fixed", fixed_count)
        self.record_sample_data("fixed_equivalencies", details)

        return {"equivalencies_fixed": fixed_count, "fix_details": details}

    @transaction.atomic
    def _create_missing_equivalencies(self) -> dict[str, Any]:
        """Create missing equivalencies between COMEX-488 and senior project courses."""
        try:
            comex_course = Course.objects.get(code="COMEX-488")
            effective_term = Term.objects.get(code="2021T3")  # When equivalencies became effective
        except (Course.DoesNotExist, Term.DoesNotExist) as e:
            self.record_rejection(
                "MISSING_COURSE" if "Course" in str(e) else "MISSING_TERM", str(e), f"Required object not found: {e}"
            )
            return {"equivalencies_created": 0}

        # Senior project courses that should have COMEX-488 equivalencies
        senior_project_codes = ["IR-489", "BUS-489", "FIN-489", "THM-433"]
        created_count = 0
        details = []

        for course_code in senior_project_codes:
            try:
                senior_course = Course.objects.get(code=course_code)
            except Course.DoesNotExist:
                self.record_rejection("MISSING_COURSE", course_code, f"Senior project course {course_code} not found")
                continue

            # Check if equivalency already exists
            existing = CourseEquivalency.objects.filter(
                models.Q(original_course=senior_course, equivalent_course=comex_course)
                | models.Q(original_course=comex_course, equivalent_course=senior_course),
                is_active=True,
            ).exists()

            if existing:
                self.stdout.write(f"  Equivalency {course_code} ↔ COMEX-488 already exists")
                self.record_rejection(
                    "EQUIVALENCY_EXISTS",
                    f"{course_code}_COMEX-488",
                    f"Equivalency between {course_code} and COMEX-488 already exists",
                )
                continue

            # Create new equivalency (unidirectional: COMEX-488 can fulfill senior project)
            equivalency = CourseEquivalency.objects.create(
                original_course=senior_course,
                equivalent_course=comex_course,
                bidirectional=False,
                effective_term=effective_term,
                reason=(
                    f"COMEX-488 (exit exam) can substitute for {course_code} "
                    "(senior project) to fulfill graduation requirement"
                ),
                is_active=True,
                approved_by_id=1,  # System user
                approval_date=timezone.now().date(),
            )

            detail = {
                "equivalency_id": equivalency.id,
                "original_course": course_code,
                "equivalent_course": "COMEX-488",
                "bidirectional": False,
                "effective_term": "2021T3",
            }
            details.append(detail)

            self.stdout.write(f"  Created equivalency: {course_code} ↔ COMEX-488")
            created_count += 1

        self.record_success("equivalencies_created", created_count)
        self.record_sample_data("created_equivalencies", details)

        return {"equivalencies_created": created_count, "equivalency_details": details}

    def _analyze_fulfillment_impact(self) -> dict[str, Any]:
        """Analyze impact on existing student fulfillments."""
        from apps.academic.models import StudentDegreeProgress

        # Find students who completed COMEX-488 and might be affected
        comex_fulfillments = StudentDegreeProgress.objects.filter(
            fulfilling_enrollment__class_header__course__code="COMEX-488", is_active=True
        ).select_related("student", "canonical_requirement__major", "fulfilling_enrollment__class_header__course")

        affected_students = set()
        impact_details = []

        for fulfillment in comex_fulfillments:
            student_id = fulfillment.student.id
            major_code = fulfillment.canonical_requirement.major.code

            affected_students.add(student_id)

            impact_details.append(
                {
                    "student_id": student_id,
                    "major_code": major_code,
                    "comex_fulfillment_id": fulfillment.id,
                    "completion_date": (
                        fulfillment.fulfillment_date.isoformat() if fulfillment.fulfillment_date else None
                    ),
                    "grade": fulfillment.grade,
                    "note": (
                        f"Student completed COMEX-488 but had it as direct requirement in "
                        f"{major_code}. Should now fulfill senior project via equivalency."
                    ),
                }
            )

        self.record_success("students_affected", len(affected_students))
        self.record_sample_data("affected_students", impact_details[:10])  # Sample only

        return {"students_affected": len(affected_students), "impact_details": impact_details}

    def generate_summary_report(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate summary report."""
        return {
            "migration_name": self.get_migration_name(),
            "timestamp": timezone.now().isoformat(),
            "summary": {
                "comex_requirements_removed": results.get("comex_requirements_removed", 0),
                "equivalencies_fixed": results.get("equivalencies_fixed", 0),
                "equivalencies_created": results.get("equivalencies_created", 0),
                "students_affected": results.get("students_affected", 0),
            },
            "business_rule_implemented": "Students can take EITHER senior project OR COMEX-488 exit exam (not both)",
            "next_steps": [
                "Run reconcile_equivalency_fulfillments command to create proper fulfillments",
                "Verify no students have both senior project AND COMEX-488 fulfillments",
                "Update academic advisor documentation about exit exam option",
            ],
            "data_integrity_check": "COMEX-488 should have NO direct canonical requirements after this migration",
        }
