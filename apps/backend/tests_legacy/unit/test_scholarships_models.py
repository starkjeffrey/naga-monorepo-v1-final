"""Unit tests for Scholarships app models.

This module tests the critical business logic of scholarship models including:
- Sponsor MOU management and date validation
- Sponsored student relationships with overlapping validation
- Scholarship eligibility rules and award calculations
- Award calculation logic (percentage vs fixed amount)
- Sponsor payment tracking and billing preferences
- Financial aid calculations and cycle-specific rules
- NGO payment modes and bulk invoicing logic

Focus on testing the "why" - the actual scholarship rules and financial aid logic.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.scholarships.models import (
    BillingCycle,
    PaymentMode,
    Scholarship,
    Sponsor,
    SponsoredStudent,
)

# Get user model for testing
User = get_user_model()


@pytest.fixture
def admin_user():
    """Create admin user for tests."""
    return User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="testpass123",
    )


@pytest.fixture
def student(db):
    """Create student profile for testing."""
    from apps.people.models import Person, StudentProfile

    person = Person.objects.create(first_name="Bob", last_name="Scholar", email="bob.scholar@example.com")

    return StudentProfile.objects.create(person=person, student_id="STU004")


@pytest.fixture
def cycle_language(db):
    """Create Language cycle for testing."""
    from apps.curriculum.models import Cycle

    return Cycle.objects.create(short_name="LANG", full_name="Language Programs", is_active=True)


@pytest.fixture
def cycle_ba(db):
    """Create BA cycle for testing."""
    from apps.curriculum.models import Cycle

    return Cycle.objects.create(short_name="BA", full_name="Bachelor's Programs", is_active=True)


@pytest.fixture
def sponsor_ngo(admin_user):
    """Create NGO sponsor for testing."""
    return Sponsor.objects.create(
        code="NGO1",
        name="Test NGO Organization",
        contact_name="Jane Donor",
        contact_email="jane@testngo.org",
        billing_email="billing@testngo.org",
        mou_start_date=date.today() - timedelta(days=30),
        mou_end_date=date.today() + timedelta(days=365),
        default_discount_percentage=Decimal("50.00"),
        requests_consolidated_invoicing=True,
        payment_mode=PaymentMode.BULK_INVOICE,
        billing_cycle=BillingCycle.TERM,
        payment_terms_days=30,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def sponsor_corporate(admin_user):
    """Create corporate sponsor for testing."""
    return Sponsor.objects.create(
        code="CORP1",
        name="Corporate Partner Ltd",
        contact_name="John Executive",
        contact_email="john@corporate.com",
        mou_start_date=date.today(),
        mou_end_date=date.today() + timedelta(days=730),
        default_discount_percentage=Decimal("25.00"),
        requests_tax_addition=True,
        payment_mode=PaymentMode.DIRECT,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.django_db
class TestSponsor:
    """Test Sponsor model business logic."""

    def test_sponsor_creation_with_mou_dates(self, admin_user):
        """Test sponsor creation with MOU date validation."""
        sponsor = Sponsor.objects.create(
            code="TEST1",
            name="Test Sponsor",
            mou_start_date=date(2024, 1, 1),
            mou_end_date=date(2024, 12, 31),
            default_discount_percentage=Decimal("30.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert sponsor.code == "TEST1"
        assert sponsor.name == "Test Sponsor"
        assert sponsor.default_discount_percentage == Decimal("30.00")
        assert sponsor.is_active is True  # Default
        assert "Test Sponsor (TEST1)" in str(sponsor)

    def test_mou_date_validation(self, admin_user):
        """Test MOU date validation logic."""
        # Test invalid MOU dates (end before start)
        with pytest.raises(ValidationError):
            sponsor = Sponsor(
                code="INVALID",
                name="Invalid Dates Sponsor",
                mou_start_date=date(2024, 12, 31),
                mou_end_date=date(2024, 1, 1),  # Before start
                created_by=admin_user,
                updated_by=admin_user,
            )
            sponsor.full_clean()

        # Test equal dates (should fail)
        with pytest.raises(ValidationError):
            sponsor = Sponsor(
                code="EQUAL",
                name="Equal Dates Sponsor",
                mou_start_date=date(2024, 6, 15),
                mou_end_date=date(2024, 6, 15),  # Same as start
                created_by=admin_user,
                updated_by=admin_user,
            )
            sponsor.full_clean()

    def test_is_mou_active_property(self, admin_user):
        """Test MOU active status determination."""
        today = date.today()

        # Active MOU (current dates)
        active_sponsor = Sponsor.objects.create(
            code="ACTIVE",
            name="Active Sponsor",
            mou_start_date=today - timedelta(days=30),
            mou_end_date=today + timedelta(days=30),
            is_active=True,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert active_sponsor.is_mou_active is True

        # Future MOU (not yet active)
        future_sponsor = Sponsor.objects.create(
            code="FUTURE",
            name="Future Sponsor",
            mou_start_date=today + timedelta(days=10),
            mou_end_date=today + timedelta(days=100),
            is_active=True,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert future_sponsor.is_mou_active is False

        # Expired MOU
        expired_sponsor = Sponsor.objects.create(
            code="EXPIRED",
            name="Expired Sponsor",
            mou_start_date=today - timedelta(days=100),
            mou_end_date=today - timedelta(days=10),
            is_active=True,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert expired_sponsor.is_mou_active is False

        # Inactive sponsor
        active_sponsor.is_active = False
        active_sponsor.save()
        assert active_sponsor.is_mou_active is False

    def test_payment_mode_configurations(self, admin_user):
        """Test different payment mode configurations."""
        # Direct payment mode
        direct_sponsor = Sponsor.objects.create(
            code="DIRECT",
            name="Direct Payment Sponsor",
            mou_start_date=date.today(),
            payment_mode=PaymentMode.DIRECT,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert direct_sponsor.payment_mode == PaymentMode.DIRECT

        # Bulk invoice mode with billing configuration
        bulk_sponsor = Sponsor.objects.create(
            code="BULK",
            name="Bulk Invoice Sponsor",
            mou_start_date=date.today(),
            payment_mode=PaymentMode.BULK_INVOICE,
            billing_cycle=BillingCycle.MONTHLY,
            invoice_generation_day=15,
            payment_terms_days=45,
            requests_consolidated_invoicing=True,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert bulk_sponsor.payment_mode == PaymentMode.BULK_INVOICE
        assert bulk_sponsor.billing_cycle == BillingCycle.MONTHLY
        assert bulk_sponsor.invoice_generation_day == 15
        assert bulk_sponsor.payment_terms_days == 45
        assert bulk_sponsor.requests_consolidated_invoicing is True

    @pytest.mark.parametrize(
        "billing_cycle",
        [
            BillingCycle.MONTHLY,
            BillingCycle.TERM,
            BillingCycle.QUARTERLY,
            BillingCycle.YEARLY,
        ],
    )
    def test_billing_cycle_options(self, admin_user, billing_cycle):
        """Test all billing cycle options."""
        sponsor = Sponsor.objects.create(
            code=f"CYCLE-{billing_cycle}",
            name=f"Test {billing_cycle} Sponsor",
            mou_start_date=date.today(),
            payment_mode=PaymentMode.BULK_INVOICE,
            billing_cycle=billing_cycle,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert sponsor.billing_cycle == billing_cycle

    def test_discount_percentage_validation(self, admin_user):
        """Test discount percentage validation (0-100)."""
        # Valid discount percentages
        valid_discounts = [
            Decimal("0.00"),
            Decimal("25.50"),
            Decimal("50.00"),
            Decimal("100.00"),
        ]

        for discount in valid_discounts:
            sponsor = Sponsor.objects.create(
                code=f"DISC-{int(discount)}",
                name=f"Discount {discount}% Sponsor",
                mou_start_date=date.today(),
                default_discount_percentage=discount,
                created_by=admin_user,
                updated_by=admin_user,
            )
            assert sponsor.default_discount_percentage == discount

        # Invalid discount percentage (over 100)
        with pytest.raises(ValidationError):
            sponsor = Sponsor(
                code="INVALID",
                name="Invalid Discount Sponsor",
                mou_start_date=date.today(),
                default_discount_percentage=Decimal("101.00"),
                created_by=admin_user,
                updated_by=admin_user,
            )
            sponsor.full_clean()

        # Invalid negative discount
        with pytest.raises(ValidationError):
            sponsor = Sponsor(
                code="NEGATIVE",
                name="Negative Discount Sponsor",
                mou_start_date=date.today(),
                default_discount_percentage=Decimal("-5.00"),
                created_by=admin_user,
                updated_by=admin_user,
            )
            sponsor.full_clean()

    def test_reporting_preferences(self, admin_user):
        """Test sponsor reporting preference combinations."""
        sponsor = Sponsor.objects.create(
            code="REPORTS",
            name="Reporting Sponsor",
            mou_start_date=date.today(),
            requests_attendance_reporting=True,
            requests_grade_reporting=True,
            requests_scheduling_reporting=False,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert sponsor.requests_attendance_reporting is True
        assert sponsor.requests_grade_reporting is True
        assert sponsor.requests_scheduling_reporting is False

    def test_admin_fee_exemption_tracking(self, admin_user):
        """Test administrative fee exemption date tracking."""
        exemption_date = date.today() + timedelta(days=180)

        sponsor = Sponsor.objects.create(
            code="EXEMPT",
            name="Fee Exempt Sponsor",
            mou_start_date=date.today(),
            admin_fee_exempt_until=exemption_date,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert sponsor.admin_fee_exempt_until == exemption_date

    def test_invoice_generation_day_validation(self, admin_user):
        """Test invoice generation day validation (1-28)."""
        # Valid days
        for day in [1, 15, 28]:
            sponsor = Sponsor.objects.create(
                code=f"DAY-{day}",
                name=f"Day {day} Sponsor",
                mou_start_date=date.today(),
                invoice_generation_day=day,
                created_by=admin_user,
                updated_by=admin_user,
            )
            assert sponsor.invoice_generation_day == day

        # Invalid day (over 28)
        with pytest.raises(ValidationError):
            sponsor = Sponsor(
                code="INVALID-DAY",
                name="Invalid Day Sponsor",
                mou_start_date=date.today(),
                invoice_generation_day=30,
                created_by=admin_user,
                updated_by=admin_user,
            )
            sponsor.full_clean()

        # Invalid day (under 1)
        with pytest.raises(ValidationError):
            sponsor = Sponsor(
                code="ZERO-DAY",
                name="Zero Day Sponsor",
                mou_start_date=date.today(),
                invoice_generation_day=0,
                created_by=admin_user,
                updated_by=admin_user,
            )
            sponsor.full_clean()


@pytest.mark.django_db
class TestSponsoredStudent:
    """Test SponsoredStudent model business logic."""

    def test_sponsored_student_creation(self, sponsor_ngo, student, admin_user):
        """Test sponsored student relationship creation."""
        sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            sponsorship_type=SponsoredStudent.SponsorshipType.FULL,
            start_date=date.today(),
            notes="Full scholarship for exceptional student",
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert sponsored.sponsor == sponsor_ngo
        assert sponsored.student == student
        assert sponsored.sponsorship_type == SponsoredStudent.SponsorshipType.FULL
        assert sponsored.end_date is None  # Ongoing
        assert "NGO1 → STU004 (FULL)" in str(sponsored)

    @pytest.mark.parametrize(
        "sponsorship_type",
        [
            SponsoredStudent.SponsorshipType.FULL,
            SponsoredStudent.SponsorshipType.PARTIAL,
            SponsoredStudent.SponsorshipType.EMERGENCY,
            SponsoredStudent.SponsorshipType.SCHOLARSHIP,
        ],
    )
    def test_sponsorship_types(self, sponsor_ngo, student, admin_user, sponsorship_type):
        """Test all sponsorship type options."""
        sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            sponsorship_type=sponsorship_type,
            start_date=date.today(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert sponsored.sponsorship_type == sponsorship_type

    def test_sponsorship_date_validation(self, sponsor_ngo, student, admin_user):
        """Test sponsorship date range validation."""
        # Test invalid date range (end before start)
        with pytest.raises(ValidationError):
            sponsored = SponsoredStudent(
                sponsor=sponsor_ngo,
                student=student,
                start_date=date(2024, 6, 15),
                end_date=date(2024, 1, 15),  # Before start
                created_by=admin_user,
                updated_by=admin_user,
            )
            sponsored.full_clean()

    def test_overlapping_sponsorship_validation(self, sponsor_ngo, student, admin_user):
        """Test validation prevents overlapping sponsorships from same sponsor."""
        # Create first sponsorship
        SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Try to create overlapping sponsorship
        with pytest.raises(ValidationError):
            overlapping = SponsoredStudent(
                sponsor=sponsor_ngo,
                student=student,
                start_date=date(2024, 3, 1),  # Overlaps existing
                end_date=date(2024, 9, 30),
                created_by=admin_user,
                updated_by=admin_user,
            )
            overlapping.full_clean()

    def test_multiple_sponsors_same_student(self, sponsor_ngo, sponsor_corporate, student, admin_user):
        """Test student can have sponsorships from different sponsors."""
        # NGO sponsorship
        ngo_sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            sponsorship_type=SponsoredStudent.SponsorshipType.PARTIAL,
            start_date=date.today(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Corporate sponsorship (different sponsor, same student)
        corporate_sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_corporate,
            student=student,
            sponsorship_type=SponsoredStudent.SponsorshipType.EMERGENCY,
            start_date=date.today(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert ngo_sponsored.sponsor != corporate_sponsored.sponsor
        assert ngo_sponsored.student == corporate_sponsored.student

    def test_is_currently_active_property(self, sponsor_ngo, student, admin_user):
        """Test sponsorship active status determination."""
        today = date.today()

        # Active sponsorship (current dates)
        active_sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=30),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert active_sponsored.is_currently_active is True

        # Future sponsorship
        future_sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=100),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert future_sponsored.is_currently_active is False

        # Expired sponsorship
        expired_sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            start_date=today - timedelta(days=100),
            end_date=today - timedelta(days=10),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert expired_sponsored.is_currently_active is False

    def test_duration_days_calculation(self, sponsor_ngo, student, admin_user):
        """Test sponsorship duration calculation."""
        start = date(2024, 1, 1)
        end = date(2024, 3, 31)  # 90 days later

        sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            start_date=start,
            end_date=end,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert sponsored.duration_days == 90

        # Ongoing sponsorship (no end date)
        ongoing = SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            start_date=date.today(),
            # No end_date
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert ongoing.duration_days is None

    def test_active_students_query_manager(self, sponsor_ngo, student, admin_user):
        """Test active sponsored students query manager."""
        today = date.today()

        # Create active sponsorship
        active_sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=20),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Query active sponsorships for this student
        active_sponsorships = SponsoredStudent.objects.get_active_for_student(student)

        assert active_sponsorships.count() == 1
        assert active_sponsored in active_sponsorships

    def test_unique_constraint_enforcement(self, sponsor_ngo, student, admin_user):
        """Test unique constraint on sponsor-student-start_date."""
        start_date = date.today()

        # Create first sponsorship
        SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            start_date=start_date,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Try to create duplicate with same start date
        with pytest.raises(Exception):  # IntegrityError
            SponsoredStudent.objects.create(
                sponsor=sponsor_ngo,
                student=student,
                start_date=start_date,  # Same start date
                created_by=admin_user,
                updated_by=admin_user,
            )


@pytest.mark.django_db
class TestScholarship:
    """Test Scholarship model business logic."""

    def test_scholarship_creation_with_percentage(self, student, cycle_language, admin_user):
        """Test scholarship creation with percentage award."""
        scholarship = Scholarship.objects.create(
            name="Merit Scholarship",
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            student=student,
            cycle=cycle_language,
            award_percentage=Decimal("75.00"),
            start_date=date.today(),
            status=Scholarship.AwardStatus.APPROVED,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert scholarship.name == "Merit Scholarship"
        assert scholarship.scholarship_type == Scholarship.ScholarshipType.MERIT
        assert scholarship.award_percentage == Decimal("75.00")
        assert scholarship.award_amount is None
        assert scholarship.award_display == "75.00%"
        assert "Merit Scholarship - STU004 (LANG)" in str(scholarship)

    def test_scholarship_creation_with_fixed_amount(self, student, cycle_ba, admin_user):
        """Test scholarship creation with fixed amount award."""
        scholarship = Scholarship.objects.create(
            name="Need-Based Grant",
            scholarship_type=Scholarship.ScholarshipType.NEED,
            student=student,
            cycle=cycle_ba,
            award_amount=Decimal("2500.00"),
            start_date=date.today(),
            status=Scholarship.AwardStatus.ACTIVE,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert scholarship.award_amount == Decimal("2500.00")
        assert scholarship.award_percentage is None
        assert scholarship.award_display == "$2500.00"

    def test_award_validation_exclusive_or(self, student, cycle_language, admin_user):
        """Test validation that scholarship has either percentage OR amount, not both."""
        # Test both percentage and amount (should fail)
        with pytest.raises(ValidationError):
            scholarship = Scholarship(
                name="Invalid Scholarship",
                scholarship_type=Scholarship.ScholarshipType.MERIT,
                student=student,
                cycle=cycle_language,
                award_percentage=Decimal("50.00"),
                award_amount=Decimal("1000.00"),  # Both set
                start_date=date.today(),
                created_by=admin_user,
                updated_by=admin_user,
            )
            scholarship.full_clean()

        # Test neither percentage nor amount (should fail for existing)
        with pytest.raises(ValidationError):
            scholarship = Scholarship(
                name="No Award Scholarship",
                scholarship_type=Scholarship.ScholarshipType.NEED,
                student=student,
                cycle=cycle_language,
                # Neither award_percentage nor award_amount set
                start_date=date.today(),
                created_by=admin_user,
                updated_by=admin_user,
            )
            # Simulate existing object by setting pk
            scholarship.pk = 1
            scholarship.full_clean()

    @pytest.mark.parametrize(
        "scholarship_type",
        [
            Scholarship.ScholarshipType.MERIT,
            Scholarship.ScholarshipType.NEED,
            Scholarship.ScholarshipType.SPONSORED,
            Scholarship.ScholarshipType.EMERGENCY,
            Scholarship.ScholarshipType.STAFF,
            Scholarship.ScholarshipType.ACADEMIC,
        ],
    )
    def test_scholarship_types(self, student, cycle_language, admin_user, scholarship_type):
        """Test all scholarship type options."""
        scholarship = Scholarship.objects.create(
            name=f"{scholarship_type} Scholarship",
            scholarship_type=scholarship_type,
            student=student,
            cycle=cycle_language,
            award_percentage=Decimal("50.00"),
            start_date=date.today(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert scholarship.scholarship_type == scholarship_type

    @pytest.mark.parametrize(
        "award_status",
        [
            Scholarship.AwardStatus.PENDING,
            Scholarship.AwardStatus.APPROVED,
            Scholarship.AwardStatus.ACTIVE,
            Scholarship.AwardStatus.SUSPENDED,
            Scholarship.AwardStatus.COMPLETED,
            Scholarship.AwardStatus.CANCELLED,
        ],
    )
    def test_scholarship_statuses(self, student, cycle_language, admin_user, award_status):
        """Test all scholarship status options."""
        scholarship = Scholarship.objects.create(
            name="Status Test Scholarship",
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            student=student,
            cycle=cycle_language,
            award_percentage=Decimal("60.00"),
            start_date=date.today(),
            status=award_status,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert scholarship.status == award_status

    def test_cycle_specific_scholarships(self, student, cycle_language, cycle_ba, admin_user):
        """Test cycle-specific scholarship business rule."""
        # Language cycle scholarship
        lang_scholarship = Scholarship.objects.create(
            name="Language Merit Award",
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            student=student,
            cycle=cycle_language,
            award_percentage=Decimal("80.00"),
            start_date=date.today(),
            status=Scholarship.AwardStatus.ACTIVE,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # BA cycle scholarship (same student, different cycle)
        ba_scholarship = Scholarship.objects.create(
            name="BA Academic Excellence",
            scholarship_type=Scholarship.ScholarshipType.ACADEMIC,
            student=student,
            cycle=cycle_ba,
            award_percentage=Decimal("70.00"),
            start_date=date.today(),
            status=Scholarship.AwardStatus.ACTIVE,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert lang_scholarship.cycle != ba_scholarship.cycle
        assert lang_scholarship.student == ba_scholarship.student

    def test_is_currently_active_property(self, student, cycle_language, admin_user):
        """Test scholarship active status determination."""
        today = date.today()

        # Active status, current dates
        active_scholarship = Scholarship.objects.create(
            name="Active Scholarship",
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            student=student,
            cycle=cycle_language,
            award_percentage=Decimal("50.00"),
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=20),
            status=Scholarship.AwardStatus.ACTIVE,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert active_scholarship.is_currently_active is True

        # Wrong status
        pending_scholarship = Scholarship.objects.create(
            name="Pending Scholarship",
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            student=student,
            cycle=cycle_language,
            award_percentage=Decimal("50.00"),
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=20),
            status=Scholarship.AwardStatus.PENDING,  # Not active/approved
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert pending_scholarship.is_currently_active is False

        # Future start date
        future_scholarship = Scholarship.objects.create(
            name="Future Scholarship",
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            student=student,
            cycle=cycle_language,
            award_percentage=Decimal("50.00"),
            start_date=today + timedelta(days=10),
            status=Scholarship.AwardStatus.APPROVED,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert future_scholarship.is_currently_active is False

    def test_sponsored_student_integration(self, sponsor_ngo, student, cycle_language, admin_user):
        """Test scholarship integration with sponsored student."""
        # Create sponsored student relationship
        sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            sponsorship_type=SponsoredStudent.SponsorshipType.SCHOLARSHIP,
            start_date=date.today(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Create scholarship linked to sponsored student
        scholarship = Scholarship.objects.create(
            name="NGO-Funded Scholarship",
            scholarship_type=Scholarship.ScholarshipType.SPONSORED,
            student=student,
            cycle=cycle_language,
            sponsored_student=sponsored,  # Link to sponsored relationship
            award_percentage=Decimal("100.00"),
            start_date=date.today(),
            status=Scholarship.AwardStatus.ACTIVE,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert scholarship.sponsored_student == sponsored
        assert scholarship.scholarship_type == Scholarship.ScholarshipType.SPONSORED

    def test_scholarship_date_validation(self, student, cycle_language, admin_user):
        """Test scholarship date range validation."""
        # Invalid date range (end before start)
        with pytest.raises(ValidationError):
            scholarship = Scholarship(
                name="Invalid Dates Scholarship",
                scholarship_type=Scholarship.ScholarshipType.MERIT,
                student=student,
                cycle=cycle_language,
                award_percentage=Decimal("50.00"),
                start_date=date(2024, 6, 15),
                end_date=date(2024, 1, 15),  # Before start
                created_by=admin_user,
                updated_by=admin_user,
            )
            scholarship.full_clean()

    def test_award_percentage_validation(self, student, cycle_language, admin_user):
        """Test award percentage validation (0-100)."""
        # Valid percentages
        for percentage in [Decimal("0.00"), Decimal("50.50"), Decimal("100.00")]:
            scholarship = Scholarship.objects.create(
                name=f"Test {percentage}% Scholarship",
                scholarship_type=Scholarship.ScholarshipType.MERIT,
                student=student,
                cycle=cycle_language,
                award_percentage=percentage,
                start_date=date.today(),
                created_by=admin_user,
                updated_by=admin_user,
            )
            assert scholarship.award_percentage == percentage

        # Invalid percentage (over 100)
        with pytest.raises(ValidationError):
            scholarship = Scholarship(
                name="Over 100% Scholarship",
                scholarship_type=Scholarship.ScholarshipType.MERIT,
                student=student,
                cycle=cycle_language,
                award_percentage=Decimal("101.00"),
                start_date=date.today(),
                created_by=admin_user,
                updated_by=admin_user,
            )
            scholarship.full_clean()

        # Invalid negative percentage
        with pytest.raises(ValidationError):
            scholarship = Scholarship(
                name="Negative Scholarship",
                scholarship_type=Scholarship.ScholarshipType.MERIT,
                student=student,
                cycle=cycle_language,
                award_percentage=Decimal("-5.00"),
                start_date=date.today(),
                created_by=admin_user,
                updated_by=admin_user,
            )
            scholarship.full_clean()

    def test_award_amount_validation(self, student, cycle_language, admin_user):
        """Test fixed award amount validation (non-negative)."""
        # Valid amounts
        for amount in [Decimal("0.00"), Decimal("1000.00"), Decimal("5000.50")]:
            scholarship = Scholarship.objects.create(
                name=f"Test ${amount} Scholarship",
                scholarship_type=Scholarship.ScholarshipType.NEED,
                student=student,
                cycle=cycle_language,
                award_amount=amount,
                start_date=date.today(),
                created_by=admin_user,
                updated_by=admin_user,
            )
            assert scholarship.award_amount == amount

        # Invalid negative amount
        with pytest.raises(ValidationError):
            scholarship = Scholarship(
                name="Negative Amount Scholarship",
                scholarship_type=Scholarship.ScholarshipType.NEED,
                student=student,
                cycle=cycle_language,
                award_amount=Decimal("-100.00"),
                start_date=date.today(),
                created_by=admin_user,
                updated_by=admin_user,
            )
            scholarship.full_clean()

    def test_unique_constraint_per_student_cycle_type(self, student, cycle_language, admin_user):
        """Test unique constraint on student-cycle-type-date for active scholarships."""
        start_date = date.today()

        # Create first active scholarship
        Scholarship.objects.create(
            name="First Merit Scholarship",
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            student=student,
            cycle=cycle_language,
            award_percentage=Decimal("70.00"),
            start_date=start_date,
            status=Scholarship.AwardStatus.ACTIVE,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Try to create duplicate active scholarship (should fail)
        with pytest.raises(Exception):  # IntegrityError
            Scholarship.objects.create(
                name="Duplicate Merit Scholarship",
                scholarship_type=Scholarship.ScholarshipType.MERIT,  # Same type
                student=student,  # Same student
                cycle=cycle_language,  # Same cycle
                award_percentage=Decimal("80.00"),
                start_date=start_date,  # Same start date
                status=Scholarship.AwardStatus.ACTIVE,  # Active status
                created_by=admin_user,
                updated_by=admin_user,
            )

    def test_award_display_formatting(self, student, cycle_language, admin_user):
        """Test award display formatting."""
        # Percentage display
        percentage_scholarship = Scholarship.objects.create(
            name="Percentage Scholarship",
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            student=student,
            cycle=cycle_language,
            award_percentage=Decimal("85.50"),
            start_date=date.today(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert percentage_scholarship.award_display == "85.50%"

        # Fixed amount display
        amount_scholarship = Scholarship.objects.create(
            name="Amount Scholarship",
            scholarship_type=Scholarship.ScholarshipType.NEED,
            student=student,
            cycle=cycle_language,
            award_amount=Decimal("1500.75"),
            start_date=date.today(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert amount_scholarship.award_display == "$1500.75"


# Integration and business logic tests
@pytest.mark.django_db
class TestScholarshipBusinessLogic:
    """Test complex scholarship business logic scenarios."""

    def test_sponsor_student_scholarship_workflow(self, sponsor_ngo, student, cycle_language, admin_user):
        """Test complete sponsor-to-scholarship workflow."""
        # Step 1: Create sponsored student relationship
        sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            sponsorship_type=SponsoredStudent.SponsorshipType.SCHOLARSHIP,
            start_date=date.today(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Step 2: Create scholarship linked to sponsorship
        scholarship = Scholarship.objects.create(
            name="NGO Language Program Scholarship",
            scholarship_type=Scholarship.ScholarshipType.SPONSORED,
            student=student,
            cycle=cycle_language,
            sponsored_student=sponsored,
            award_percentage=sponsor_ngo.default_discount_percentage,  # Use sponsor's default
            start_date=sponsored.start_date,
            status=Scholarship.AwardStatus.ACTIVE,
            description="Full scholarship funded by NGO partnership",
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Verify integrated workflow
        assert scholarship.sponsored_student == sponsored
        assert scholarship.award_percentage == sponsor_ngo.default_discount_percentage
        assert scholarship.start_date == sponsored.start_date
        assert scholarship.is_currently_active is True
        assert sponsored.is_currently_active is True

    def test_cycle_transition_scholarship_reentry(self, student, cycle_language, cycle_ba, admin_user):
        """Test scholarship reentry when transitioning between cycles."""
        # Language cycle scholarship (completed)
        lang_scholarship = Scholarship.objects.create(
            name="Language Program Merit",
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            student=student,
            cycle=cycle_language,
            award_percentage=Decimal("60.00"),
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            status=Scholarship.AwardStatus.COMPLETED,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Student transitions to BA - must reapply/re-enter
        ba_scholarship = Scholarship.objects.create(
            name="BA Academic Excellence",
            scholarship_type=Scholarship.ScholarshipType.ACADEMIC,
            student=student,
            cycle=cycle_ba,  # Different cycle
            award_percentage=Decimal("70.00"),  # Potentially different amount
            start_date=date(2024, 1, 1),
            status=Scholarship.AwardStatus.ACTIVE,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Verify cycle separation
        assert lang_scholarship.cycle != ba_scholarship.cycle
        assert lang_scholarship.status == Scholarship.AwardStatus.COMPLETED
        assert ba_scholarship.status == Scholarship.AwardStatus.ACTIVE
        assert not lang_scholarship.is_currently_active
        assert ba_scholarship.is_currently_active

    def test_multiple_sponsors_coordination(self, sponsor_ngo, sponsor_corporate, student, cycle_ba, admin_user):
        """Test coordination between multiple sponsors for same student."""
        # NGO provides partial funding
        ngo_sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_ngo,
            student=student,
            sponsorship_type=SponsoredStudent.SponsorshipType.PARTIAL,
            start_date=date.today(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        ngo_scholarship = Scholarship.objects.create(
            name="NGO Partial Scholarship",
            scholarship_type=Scholarship.ScholarshipType.SPONSORED,
            student=student,
            cycle=cycle_ba,
            sponsored_student=ngo_sponsored,
            award_percentage=Decimal("50.00"),  # Partial funding
            start_date=date.today(),
            status=Scholarship.AwardStatus.ACTIVE,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Corporate provides additional emergency support
        corporate_sponsored = SponsoredStudent.objects.create(
            sponsor=sponsor_corporate,
            student=student,
            sponsorship_type=SponsoredStudent.SponsorshipType.EMERGENCY,
            start_date=date.today(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        emergency_scholarship = Scholarship.objects.create(
            name="Corporate Emergency Grant",
            scholarship_type=Scholarship.ScholarshipType.EMERGENCY,
            student=student,
            cycle=cycle_ba,
            sponsored_student=corporate_sponsored,
            award_amount=Decimal("1000.00"),  # Fixed emergency amount
            start_date=date.today(),
            status=Scholarship.AwardStatus.ACTIVE,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Verify multiple active scholarships coordination
        active_scholarships = Scholarship.objects.filter(
            student=student,
            status__in=[Scholarship.AwardStatus.ACTIVE, Scholarship.AwardStatus.APPROVED],
            cycle=cycle_ba,
        )

        assert active_scholarships.count() == 2
        assert ngo_scholarship in active_scholarships
        assert emergency_scholarship in active_scholarships

        # Total potential coverage (50% + $1000 fixed)
        percentage_award = ngo_scholarship.award_percentage
        fixed_award = emergency_scholarship.award_amount

        assert percentage_award == Decimal("50.00")
        assert fixed_award == Decimal("1000.00")

    def test_scholarship_status_lifecycle(self, student, cycle_language, admin_user):
        """Test complete scholarship status lifecycle."""
        scholarship = Scholarship.objects.create(
            name="Lifecycle Test Scholarship",
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            student=student,
            cycle=cycle_language,
            award_percentage=Decimal("80.00"),
            start_date=date.today() + timedelta(days=30),  # Future start
            status=Scholarship.AwardStatus.PENDING,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Step 1: Pending review
        assert scholarship.status == Scholarship.AwardStatus.PENDING
        assert not scholarship.is_currently_active  # Not active status

        # Step 2: Approved
        scholarship.status = Scholarship.AwardStatus.APPROVED
        scholarship.save()

        assert scholarship.status == Scholarship.AwardStatus.APPROVED
        assert not scholarship.is_currently_active  # Future start date

        # Step 3: Active (adjust start date)
        scholarship.start_date = date.today()
        scholarship.status = Scholarship.AwardStatus.ACTIVE
        scholarship.save()

        assert scholarship.status == Scholarship.AwardStatus.ACTIVE
        assert scholarship.is_currently_active  # Now active

        # Step 4: Suspended temporarily
        scholarship.status = Scholarship.AwardStatus.SUSPENDED
        scholarship.save()

        assert scholarship.status == Scholarship.AwardStatus.SUSPENDED
        assert not scholarship.is_currently_active  # Suspended

        # Step 5: Reactivated
        scholarship.status = Scholarship.AwardStatus.ACTIVE
        scholarship.save()

        assert scholarship.is_currently_active  # Active again

        # Step 6: Completed
        scholarship.status = Scholarship.AwardStatus.COMPLETED
        scholarship.end_date = date.today()
        scholarship.save()

        assert scholarship.status == Scholarship.AwardStatus.COMPLETED
        assert not scholarship.is_currently_active  # Completed

    def test_sponsor_payment_mode_impact(self, sponsor_ngo, sponsor_corporate, student, cycle_ba, admin_user):
        """Test how sponsor payment modes affect scholarship processing."""
        # NGO with bulk invoice mode
        assert sponsor_ngo.payment_mode == PaymentMode.BULK_INVOICE
        assert sponsor_ngo.requests_consolidated_invoicing is True
        assert sponsor_ngo.billing_cycle == BillingCycle.TERM

        # Corporate with direct payment mode
        assert sponsor_corporate.payment_mode == PaymentMode.DIRECT

        # Create scholarships for each sponsor type
        bulk_scholarship = Scholarship.objects.create(
            name="Bulk Invoice Scholarship",
            scholarship_type=Scholarship.ScholarshipType.SPONSORED,
            student=student,
            cycle=cycle_ba,
            award_percentage=Decimal("100.00"),
            start_date=date.today(),
            status=Scholarship.AwardStatus.ACTIVE,
            created_by=admin_user,
            updated_by=admin_user,
        )

        direct_scholarship = Scholarship.objects.create(
            name="Direct Payment Scholarship",
            scholarship_type=Scholarship.ScholarshipType.SPONSORED,
            student=student,
            cycle=cycle_ba,
            award_percentage=Decimal("25.00"),
            start_date=date.today(),
            status=Scholarship.AwardStatus.ACTIVE,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Verify different payment processing expectations
        # (Business logic would be implemented in services/billing integration)
        assert bulk_scholarship.award_percentage == Decimal("100.00")
        assert direct_scholarship.award_percentage == Decimal("25.00")
