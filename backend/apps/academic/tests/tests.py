"""Simple tests for academic app models to validate test infrastructure works.

This is a simplified test suite that validates the test infrastructure is working
correctly after the major codebase cleanup and formatting improvements.
"""

from django.test import TestCase

from apps.academic.models import CanonicalRequirement


class AcademicModelsSimpleTest(TestCase):
    """Simple test to validate test infrastructure works."""

    def test_can_import_models(self):
        """Test that we can import all academic models without errors."""
        from apps.academic.models import (
            CanonicalRequirement,
            CourseEquivalency,
            StudentCourseOverride,
            StudentDegreeProgress,
            StudentRequirementException,
            TransferCredit,
        )

        # If we get here without ImportError, the models are properly structured
        assert CanonicalRequirement is not None
        assert CourseEquivalency is not None
        assert TransferCredit is not None
        assert StudentDegreeProgress is not None
        assert StudentRequirementException is not None
        assert StudentCourseOverride is not None

    def test_canonical_requirement_model_exists(self):
        """Test that CanonicalRequirement model has expected attributes."""
        # Check that the model has the expected fields without creating instances
        field_names = [field.name for field in CanonicalRequirement._meta.get_fields()]

        expected_fields = ["major", "sequence_number", "required_course", "name", "effective_term"]
        for field in expected_fields:
            assert field in field_names, f"Expected field '{field}' not found in CanonicalRequirement"

    def test_meta_information(self):
        """Test model meta information is correct."""
        assert CanonicalRequirement._meta.app_label == "academic"
        assert CanonicalRequirement._meta.verbose_name == "Canonical Requirement"

        # Check ordering
        assert CanonicalRequirement._meta.ordering == ["major", "sequence_number"]
