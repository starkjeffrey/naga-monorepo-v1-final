"""Example usage of ClassPartTemplate system.

This script demonstrates how to:
1. Create templates for a language program level
2. Apply templates when creating new classes
3. Promote students with template application
"""

from decimal import Decimal

from django.utils import timezone

from apps.scheduling.services.template_service import (
    ClassTemplateService,
    StudentPromotionService,
)


def create_ehss_level_7_template():
    """Create a template for EHSS Level 7 with the Ventures structure."""

    # Define the parts for EHSS Level 7
    parts_config = [
        {
            "name": "Ventures",
            "class_part_type": "MAIN",
            "class_part_code": "A",
            "meeting_days_pattern": "MON,WED",
            "grade_weight": Decimal("0.40"),
            "sequence_order": 1,
        },
        {
            "name": "Reading",
            "class_part_type": "READING",
            "class_part_code": "B",
            "meeting_days_pattern": "TUE,THU",
            "grade_weight": Decimal("0.40"),
            "sequence_order": 2,
        },
        {
            "name": "Computer Training",
            "class_part_type": "COMPUTER",
            "class_part_code": "C",
            "meeting_days_pattern": "FRI",
            "grade_weight": Decimal("0.20"),
            "sequence_order": 3,
        },
    ]

    # Create the template set
    service = ClassTemplateService()
    template_set = service.create_template_set(
        program_code="EHSS",
        level_number=7,
        parts_config=parts_config,
        effective_date=timezone.now().date(),
        name="EHSS Level 7 - Ventures Structure",
    )

    print(f"Created template: {template_set}")
    print(f"With {len(parts_config)} parts:")
    for part in template_set.templates.all():
        print(f"  - {part.name} ({part.class_part_code}): {part.meeting_days_pattern}, weight={part.grade_weight}")

    return template_set


def apply_template_to_new_class():
    """Demonstrate applying a template when creating a new class."""

    from apps.scheduling.models import ClassHeader

    # Create a new EHSS Level 7 class
    new_class = ClassHeader.objects.create(
        program="EHSS",
        level_number=7,
        section="A",
        term_id="2024-SPRING",
        max_enrollment=20,
        course_code="EHSS-07",
        course_name="EHSS Level 7",
    )

    # Apply the template
    service = ClassTemplateService()
    created_parts = service.apply_template_to_class(
        class_header=new_class,
        term="2024-SPRING",
    )

    print(f"\nApplied template to class {new_class}")
    print(f"Created {len(created_parts)} parts:")
    for part in created_parts:
        print(f"  - {part.name} ({part.class_part_code}): {part.meeting_days}, weight={part.grade_weight}")

    return new_class, created_parts


def promote_students_example():
    """Demonstrate promoting students from EHSS Level 6 to Level 7."""

    from apps.people.models import StudentProfile
    from apps.scheduling.models import ClassHeader

    # Get source class (EHSS Level 6)
    source_class = ClassHeader.objects.filter(
        program="EHSS",
        level_number=6,
        is_active=True,
    ).first()

    if not source_class:
        print("No active EHSS Level 6 class found")
        return

    # Get students to promote (in real scenario, these would be passing students)
    students = StudentProfile.objects.filter(
        enrollments__class_header=source_class,
        enrollments__is_active=True,
    ).distinct()[:10]  # Just take first 10 for example

    # Promote students
    service = StudentPromotionService()
    results = service.promote_students(
        students=list(students),
        source_class=source_class,
        destination_program="EHSS",
        destination_level=7,
        new_term="2024-SPRING",
        preserve_cohort=True,  # Keep students together
    )

    print("\nPromotion Results:")
    print(f"  - Promoted {len(results['promoted'])} students")
    print(f"  - Created {len(results['new_classes'])} new classes")

    for new_class in results["new_classes"]:
        print(f"\nNew class: {new_class}")
        # The template was automatically applied
        parts = new_class.sessions.first().class_parts.all()
        for part in parts:
            print(f"  - {part.name} ({part.class_part_code}): {part.meeting_days}")

    return results


def bulk_promotion_example():
    """Demonstrate bulk promotion of all EHSS Level 6 students to Level 7."""

    service = StudentPromotionService()
    results = service.bulk_promote_level(
        source_program="EHSS",
        source_level=6,
        destination_program="EHSS",
        destination_level=7,
        term="2024-SPRING",
    )

    print("\nBulk Promotion Results:")
    print(f"  - Total promoted: {results['total_promoted']} students")
    print(f"  - Total classes created: {results['total_classes_created']}")

    return results


if __name__ == "__main__":
    # Example 1: Create a template
    print("=" * 60)
    print("Example 1: Creating EHSS Level 7 Template")
    print("=" * 60)
    template = create_ehss_level_7_template()

    # Example 2: Apply template to a new class
    print("\n" + "=" * 60)
    print("Example 2: Applying Template to New Class")
    print("=" * 60)
    new_class, parts = apply_template_to_new_class()

    # Example 3: Promote students with template application
    print("\n" + "=" * 60)
    print("Example 3: Promoting Students")
    print("=" * 60)
    promotion_results = promote_students_example()

    # Example 4: Bulk promotion
    print("\n" + "=" * 60)
    print("Example 4: Bulk Level Promotion")
    print("=" * 60)
    bulk_results = bulk_promotion_example()
