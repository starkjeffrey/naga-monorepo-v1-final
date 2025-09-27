"""Simple test-only factories for scholarships tests.

These factories create minimal test data without complex dependencies
to ensure tests can run independently.
"""

from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.scholarships.models import Scholarship, Sponsor, SponsoredStudent


class SimpleSponsorFactory(DjangoModelFactory):
    """Simple factory for creating test sponsors."""

    class Meta:
        model = Sponsor

    code = factory.Sequence(lambda n: f"TEST{n}")
    name = factory.LazyAttribute(lambda obj: f"Test Sponsor {obj.code}")
    contact_name = factory.Faker("name")
    contact_email = factory.LazyAttribute(lambda obj: f"contact@{obj.code.lower()}.org")
    contact_phone = "+85512345678"
    billing_email = factory.LazyAttribute(lambda obj: f"billing@{obj.code.lower()}.org")

    mou_start_date = factory.LazyFunction(lambda: timezone.now().date() - timedelta(days=30))
    mou_end_date = factory.LazyFunction(lambda: timezone.now().date() + timedelta(days=365))

    default_discount_percentage = Decimal("75.00")
    requests_tax_addition = False
    requests_consolidated_invoicing = True
    admin_fee_exempt_until = None

    requests_attendance_reporting = True
    requests_grade_reporting = True
    requests_scheduling_reporting = False

    is_active = True
    notes = ""


class SimpleSponsoredStudentFactory(DjangoModelFactory):
    """Simple factory for creating test sponsored students."""

    class Meta:
        model = SponsoredStudent

    sponsor = factory.SubFactory(SimpleSponsorFactory)
    # student will be set manually in tests

    sponsorship_type = SponsoredStudent.SponsorshipType.FULL
    start_date = factory.LazyFunction(lambda: timezone.now().date() - timedelta(days=30))
    end_date = factory.LazyFunction(lambda: timezone.now().date() + timedelta(days=365))
    notes = ""


class SimpleScholarshipFactory(DjangoModelFactory):
    """Simple factory for creating test scholarships."""

    class Meta:
        model = Scholarship

    name = factory.Faker("sentence", nb_words=3)
    scholarship_type = Scholarship.ScholarshipType.MERIT
    # student and cycle will be set manually in tests
    sponsored_student = None
    cycle = None

    award_percentage = Decimal("75.00")
    award_amount = None

    start_date = factory.LazyFunction(lambda: timezone.now().date() - timedelta(days=30))
    end_date = factory.LazyFunction(lambda: timezone.now().date() + timedelta(days=365))

    status = Scholarship.AwardStatus.ACTIVE
    description = ""
    conditions = ""
    notes = ""
