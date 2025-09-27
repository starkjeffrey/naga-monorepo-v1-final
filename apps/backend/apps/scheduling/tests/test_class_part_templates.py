"""Tests for ClassPartTemplate functionality.

This module tests the ClassPartTemplate system including:
- Template creation and validation
- Template versioning and effective dates
- Template application to classes
- Promotion logic with mandatory templates
- Language class validation
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TransactionTestCase
from django.utils import timezone

from apps.curriculum.models import Course, Term
from apps.scheduling.models import ClassHeader, ClassPart, ClassSession
from apps.scheduling.models_templates import (
    ClassPartTemplate,
    ClassPartTemplateSet,
    ClassPromotionRule,
)
from apps.scheduling.template_services.template_service import (
    ClassTemplateService,
)
from apps.scheduling.validators import (
    validate_class_has_proper_structure,
    validate_language_class_creation,
)


class ClassPartTemplateModelTests(TransactionTestCase):
    """Test ClassPartTemplate model functionality."""

    def setUp(self):
        """Set up test data."""
        from apps.curriculum.models import Cycle, Division

        # Create required division and cycle
        self.division = Division.objects.create(name="English Language", short_name="ENG")
        self.cycle = Cycle.objects.create(name="2024 Cycle", division=self.division)

        # Create a test term
        self.term = Term.objects.create(
            code="2024-SPRING",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 5, 15),
        )

        # Create test language courses
        self.ehss_07_course = Course.objects.create(
            code="EHSS-07",
            title="EHSS Level 7",
            credits=6,
            cycle=self.cycle,
        )

        self.ehss_08_course = Course.objects.create(
            code="EHSS-08",
            title="EHSS Level 8",
            credits=6,
            cycle=self.cycle,
        )

    def test_create_template_set(self):
        """Test creating a ClassPartTemplateSet."""
        template_set = ClassPartTemplateSet.objects.create(
            program_code="EHSS",
            level_number=7,
            effective_date=timezone.now().date(),
            name="EHSS Level 7 Template",
            description="Template for EHSS Level 7 classes",
            version=1,
        )

        self.assertEqual(template_set.level_code, "EHSS-07")
        self.assertTrue(template_set.is_current())
        self.assertEqual(str(template_set), f"EHSS-07 v1 ({template_set.effective_date})")

    def test_create_template_parts(self):
        """Test creating ClassPartTemplate instances."""
        template_set = ClassPartTemplateSet.objects.create(
            program_code="EHSS",
            level_number=7,
            effective_date=timezone.now().date(),
            name="EHSS Level 7 Template",
        )

        # Create parts
        part_a = ClassPartTemplate.objects.create(
            template_set=template_set,
            class_part_type="MAIN",
            class_part_code="A",
            name="Ventures",
            meeting_days_pattern="MON,WED",
            grade_weight=Decimal("0.40"),
            sequence_order=1,
        )

        ClassPartTemplate.objects.create(
            template_set=template_set,
            class_part_type="READING",
            class_part_code="B",
            name="Reading",
            meeting_days_pattern="TUE,THU",
            grade_weight=Decimal("0.40"),
            sequence_order=2,
        )

        ClassPartTemplate.objects.create(
            template_set=template_set,
            class_part_type="COMPUTER",
            class_part_code="C",
            name="Computer Training",
            meeting_days_pattern="FRI",
            grade_weight=Decimal("0.20"),
            sequence_order=3,
        )

        self.assertEqual(template_set.templates.count(), 3)
        self.assertEqual(part_a.template_set, template_set)
        self.assertEqual(str(part_a), "EHSS-07 - Ventures (A)")

    def test_template_versioning(self):
        """Test that only one template can be active per program/level."""
        # Create first template
        template_v1 = ClassPartTemplateSet.objects.create(
            program_code="EHSS",
            level_number=7,
            effective_date=timezone.now().date(),
            name="EHSS Level 7 Template v1",
            version=1,
            is_active=True,
        )

        # Create second template for same level (effective today)
        template_v2 = ClassPartTemplateSet.objects.create(
            program_code="EHSS",
            level_number=7,
            effective_date=timezone.now().date(),
            name="EHSS Level 7 Template v2",
            version=2,
            is_active=True,
        )

        # Expire the first template (set to yesterday)
        yesterday = timezone.now().date() - timedelta(days=1)
        template_v1.expiry_date = yesterday
        template_v1.save()

        # Check that get_current returns v2
        current = ClassPartTemplateSet.get_current_for_level("EHSS", 7)
        self.assertEqual(current, template_v2)

    def test_invalid_meeting_days_pattern(self):
        """Test that invalid meeting days are rejected."""
        template_set = ClassPartTemplateSet.objects.create(
            program_code="EHSS",
            level_number=7,
            effective_date=timezone.now().date(),
            name="EHSS Level 7 Template",
        )

        part = ClassPartTemplate(
            template_set=template_set,
            class_part_type="MAIN",
            class_part_code="A",
            name="Test Part",
            meeting_days_pattern="INVALID,DAY",
            grade_weight=Decimal("1.00"),
        )

        with self.assertRaises(ValidationError) as context:
            part.clean()

        self.assertIn("Invalid days", str(context.exception))


class TemplateApplicationTests(TransactionTestCase):
    """Test applying templates to classes."""

    def setUp(self):
        """Set up test data."""
        from apps.curriculum.models import Cycle, Division

        # Create required division and cycle
        self.division = Division.objects.create(name="English Language", short_name="ENG")
        self.cycle = Cycle.objects.create(name="2024 Cycle", division=self.division)

        self.term = Term.objects.create(
            code="2024-SPRING",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 5, 15),
        )

        self.course = Course.objects.create(
            code="EHSS-07",
            title="EHSS Level 7",
            credits=6,
            cycle=self.cycle,
        )

        # Create a template
        self.service = ClassTemplateService()
        self.template_set = self.service.create_template_set(
            program_code="EHSS",
            level_number=7,
            parts_config=[
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
            ],
        )

    def test_apply_template_to_class(self):
        """Test applying a template to create class parts."""
        # Create a class
        class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
            max_enrollment=20,
        )

        # Apply template
        created_parts = self.service.apply_template_to_class(
            class_header=class_header,
            term=self.term.code,
        )

        self.assertEqual(len(created_parts), 3)

        # Check parts were created correctly
        parts = ClassPart.objects.filter(class_session__class_header=class_header).order_by("class_part_code")

        self.assertEqual(parts.count(), 3)

        # Check first part
        part_a = parts.first()
        self.assertEqual(part_a.name, "Ventures")
        self.assertEqual(part_a.class_part_code, "A")
        self.assertEqual(part_a.meeting_days, "MON,WED")
        self.assertEqual(part_a.grade_weight, Decimal("0.40"))
        self.assertTrue(part_a.template_derived)

    def test_template_required_for_language_class(self):
        """Test that language classes cannot be created without templates."""
        # Create a course without a template
        gesl_course = Course.objects.create(
            code="GESL-05",
            title="GESL Level 5",
            credits=6,
            cycle=self.cycle,
        )

        # Try to validate class creation
        with self.assertRaises(ValidationError) as context:
            validate_language_class_creation(gesl_course)

        self.assertIn("No ClassPartTemplate defined", str(context.exception))

    def test_ba_class_does_not_require_template(self):
        """Test that BA/MA classes don't require templates."""
        ba_course = Course.objects.create(
            code="BA-PSYC-101",
            title="Introduction to Psychology",
            credits=3,
            cycle=self.cycle,
        )

        # Should not raise an error
        try:
            validate_language_class_creation(ba_course)
        except ValidationError:
            self.fail("BA course should not require a template")


class PromotionRuleTests(TransactionTestCase):
    """Test promotion rules and logic."""

    def setUp(self):
        """Set up test data."""
        self.source_term = Term.objects.create(
            code="2024-SPRING",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 5, 15),
        )

        self.target_term = Term.objects.create(
            code="2024-FALL",
            start_date=date(2024, 8, 15),
            end_date=date(2024, 12, 15),
        )

    def test_create_promotion_rule(self):
        """Test creating a promotion rule."""
        rule = ClassPromotionRule.objects.create(
            source_program="EHSS",
            source_level=6,
            destination_program="EHSS",
            destination_level=7,
            preserve_cohort=True,
            auto_create_classes=True,
            apply_template=True,
        )

        self.assertEqual(str(rule), "EHSS-06 → EHSS-07")
        self.assertTrue(rule.preserve_cohort)
        self.assertTrue(rule.apply_template)

    def test_promotion_requires_template(self):
        """Test that promotion fails without target level template."""
        # Create source class without template (will fail in real scenario)
        # For testing, we'll check the validation logic

        # Import the enhanced service
        from apps.language.services_updated import EnhancedLanguagePromotionService

        # Validate templates exist
        exists, missing = EnhancedLanguagePromotionService.validate_templates_exist(
            program="EHSS",
            start_level=7,
            end_level=8,
        )

        self.assertFalse(exists)
        self.assertIn("EHSS-07", missing)
        self.assertIn("EHSS-08", missing)


class ValidatorTests(TransactionTestCase):
    """Test validation functions."""

    def setUp(self):
        """Set up test data."""
        from apps.curriculum.models import Cycle, Division

        # Create required division and cycle
        self.division = Division.objects.create(name="English Language", short_name="ENG")
        self.cycle = Cycle.objects.create(name="2024 Cycle", division=self.division)

        self.term = Term.objects.create(
            code="2024-SPRING",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 5, 15),
        )

    def test_validate_class_structure(self):
        """Test validating class structure for language classes."""
        # Create a language course
        course = Course.objects.create(
            code="EHSS-07",
            title="EHSS Level 7",
            credits=6,
            cycle=self.cycle,
        )

        # Create a class without parts (invalid for language)
        class_header = ClassHeader.objects.create(
            course=course,
            term=self.term,
            section_id="A",
        )

        # Create session but no parts
        ClassSession.objects.create(
            class_header=class_header,
            session_number=1,
            grade_weight=Decimal("1.00"),
        )

        # Validate structure
        result = validate_class_has_proper_structure(class_header)

        self.assertFalse(result["valid"])
        self.assertIn("has no class parts", result["errors"][0])

    def test_validate_template_derived_parts(self):
        """Test that language class parts should be template-derived."""
        # Create a language course
        course = Course.objects.create(
            code="GESL-03",
            title="GESL Level 3",
            credits=6,
            cycle=self.cycle,
        )

        class_header = ClassHeader.objects.create(
            course=course,
            term=self.term,
            section_id="A",
        )

        session = ClassSession.objects.create(
            class_header=class_header,
            session_number=1,
            grade_weight=Decimal("1.00"),
        )

        # Create a part manually (not from template)
        ClassPart.objects.create(
            class_session=session,
            class_part_type="MAIN",
            class_part_code="A",
            name="Manual Part",
            meeting_days="MON,WED",
            grade_weight=Decimal("1.00"),
            template_derived=False,  # Not from template
        )

        # Validate structure
        result = validate_class_has_proper_structure(class_header)

        self.assertFalse(result["valid"])
        self.assertIn("not created from template", result["errors"][0])


class IntegrationTests(TransactionTestCase):
    """Integration tests for the complete workflow."""

    def setUp(self):
        """Set up test data."""
        from apps.curriculum.models import Cycle, Division

        # Create required division and cycle
        self.division = Division.objects.create(name="English Language", short_name="ENG")
        self.cycle = Cycle.objects.create(name="2024 Cycle", division=self.division)

        self.term = Term.objects.create(
            code="2024-SPRING",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 5, 15),
        )

        # Create courses for multiple levels
        self.ehss_06_course = Course.objects.create(
            code="EHSS-06",
            title="EHSS Level 6",
            credits=6,
            cycle=self.cycle,
        )

        self.ehss_07_course = Course.objects.create(
            code="EHSS-07",
            title="EHSS Level 7",
            credits=6,
            cycle=self.cycle,
        )

        # Create templates for level 7
        self.service = ClassTemplateService()
        self.template_set = self.service.create_template_set(
            program_code="EHSS",
            level_number=7,
            parts_config=[
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
            ],
        )

    def test_complete_workflow(self):
        """Test the complete workflow from template creation to class creation."""
        # 1. Verify template exists
        current_template = ClassPartTemplateSet.get_current_for_level("EHSS", 7)
        self.assertIsNotNone(current_template)
        self.assertEqual(current_template.templates.count(), 3)

        # 2. Create a class with template
        class_header = ClassHeader.objects.create(
            course=self.ehss_07_course,
            term=self.term,
            section_id="A",
            max_enrollment=20,
        )

        # 3. Apply template
        created_parts = self.service.apply_template_to_class(
            class_header=class_header,
            term=self.term.code,
        )

        # 4. Verify class structure
        self.assertEqual(len(created_parts), 3)

        # Check all parts
        parts = ClassPart.objects.filter(class_session__class_header=class_header).order_by("class_part_code")

        self.assertEqual(parts.count(), 3)

        # Verify each part
        part_names = [p.name for p in parts]
        self.assertIn("Ventures", part_names)
        self.assertIn("Reading", part_names)
        self.assertIn("Computer Training", part_names)

        # All should be template-derived
        for part in parts:
            self.assertTrue(part.template_derived)

        # 5. Validate structure
        validation = validate_class_has_proper_structure(class_header)
        self.assertTrue(validation["valid"])

    def test_class_creation_blocked_without_template(self):
        """Test that class creation is blocked when template is missing."""
        # Create a course for a level without template
        ieap_course = Course.objects.create(
            code="IEAP-02",
            title="IEAP Level 2",
            credits=8,
            cycle=self.cycle,
        )

        # Try to create a class (should fail validation)
        class_header = ClassHeader(
            course=ieap_course,
            term=self.term,
            section_id="A",
        )

        with self.assertRaises(ValidationError) as context:
            class_header.clean()

        self.assertIn("No ClassPartTemplate defined", str(context.exception))
