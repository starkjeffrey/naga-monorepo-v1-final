"""
Unit tests for analytics services.

Tests the analytics service functionality for generating student progress reports
and academic analytics.
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.analytics.services import ProgramJourneyAnalyzer


@pytest.fixture
def analytics_service():
    """Create a ProgramJourneyAnalyzer instance."""
    return ProgramJourneyAnalyzer()


def test_analyze_student_journey_no_enrollments(analytics_service):
    """Test student journey analysis with no enrollments."""
    # Mock student with no enrollments
    mock_student = MagicMock(id=1, student_id="12345")

    with patch("apps.analytics.services.ClassHeaderEnrollment") as mock_enrollment:
        mock_enrollment.objects.filter.return_value.select_related.return_value.order_by.return_value = []

        result = analytics_service.analyze_student_journey(mock_student)

        assert "status" in result
        assert result["status"] == "NO_ENROLLMENTS"


def test_deduce_major_from_courses_empty(analytics_service):
    """Test major deduction with empty course list."""
    result = analytics_service._deduce_major_from_courses([])

    assert result is None


def test_deduce_major_from_courses_with_data(analytics_service):
    """Test major deduction with course data."""
    # Mock courses with different prefixes
    mock_courses = [
        MagicMock(code="IR-101"),
        MagicMock(code="IR-201"),
        MagicMock(code="BUS-101"),
    ]

    result = analytics_service._deduce_major_from_courses(mock_courses)

    assert result is not None
    assert "major" in result
    assert "confidence" in result
    assert "primary_prefix" in result
    assert result["primary_prefix"] == "IR"
    assert result["major"] == "International Relations"


def test_classify_journey_type_linear(analytics_service):
    """Test journey type classification for linear journey."""
    periods = [{"division": "ACADEMIC", "cycle": "BA"}]

    result = analytics_service._classify_journey_type(periods)

    assert result == "LINEAR"


def test_classify_journey_type_ba_to_ma(analytics_service):
    """Test journey type classification for BA to MA progression."""
    periods = [{"division": "ACADEMIC", "cycle": "BA"}, {"division": "ACADEMIC", "cycle": "MA"}]

    result = analytics_service._classify_journey_type(periods)

    assert result == "BA_TO_MA_PROGRESSION"


def test_identify_gaps_empty_terms(analytics_service):
    """Test gap identification with empty terms."""
    gaps = analytics_service._identify_gaps([])

    assert len(gaps) == 0


def test_service_initialization():
    """Test that analytics service initializes properly."""
    service = ProgramJourneyAnalyzer()
    assert service is not None
    assert isinstance(service, ProgramJourneyAnalyzer)
