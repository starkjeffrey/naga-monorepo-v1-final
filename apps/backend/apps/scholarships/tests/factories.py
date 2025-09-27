"""Factory-boy factories for scholarship models.

This module provides factory classes for generating realistic test data
for scholarship and sponsorship models including:
- Sponsor organizations with MOU tracking
- Sponsored student relationships
- Scholarship awards and applications
- Financial aid management

Following clean architecture principles with realistic data generation
that supports comprehensive testing of scholarship workflows.
"""

from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

from apps.scholarships.constants import (
    COMMON_SPONSORS,
    MERIT_SCHOLARSHIP_TYPES,
    STANDARD_DISCOUNTS,
)
from apps.scholarships.models import Scholarship, Sponsor, SponsoredStudent


class SponsorFactory(DjangoModelFactory):
    """Factory for creating sponsor organizations."""

    class Meta:
        model = Sponsor
        django_get_or_create = ("code",)

    code = Faker("random_element", elements=list(COMMON_SPONSORS.keys()))

    name = factory.LazyAttribute(lambda obj: COMMON_SPONSORS.get(obj.code, f"{obj.code} Foundation"))

    contact_name = Faker("name")
    contact_email = factory.LazyAttribute(
        lambda obj: (
            f"{obj.contact_name.lower().replace(' ', '.')}@{obj.code.lower()}.org" if obj.contact_name else ""
        ),
    )
    contact_phone = factory.LazyAttribute(lambda obj: f"+855{Faker('numerify', text='#######').evaluate()}"[:20])
    billing_email = factory.LazyAttribute(lambda obj: f"billing@{obj.code.lower()}.org")

    # MOU dates - typically 1-5 year agreements
    mou_start_date = Faker("date_between", start_date="-2y", end_date="today")
    mou_end_date = factory.LazyAttribute(
        lambda obj: obj.mou_start_date + timedelta(days=1095),  # 3 years
    )

    # Financial preferences using constants
    default_discount_percentage = Faker(
        "random_element",
        elements=list(STANDARD_DISCOUNTS.values()),
    )

    # Billing preferences
    requests_tax_addition = Faker("boolean", chance_of_getting_true=30)
    requests_consolidated_invoicing = Faker("boolean", chance_of_getting_true=70)

    # Admin fee exemption
    admin_fee_exempt_until = factory.LazyAttribute(
        lambda obj: obj.mou_start_date + timedelta(days=365),  # 1 year
    )

    # Reporting requirements
    requests_attendance_reporting = Faker("boolean", chance_of_getting_true=80)
    requests_grade_reporting = Faker("boolean", chance_of_getting_true=85)
    requests_scheduling_reporting = Faker("boolean", chance_of_getting_true=60)

    is_active = Faker("boolean", chance_of_getting_true=90)

    notes = factory.LazyAttribute(
        lambda obj: (
            f"Partnership with {obj.name} focusing on educational development in Cambodia."
            if Faker("boolean", chance_of_getting_true=40)
            else ""
        ),
    )


class SponsoredStudentFactory(DjangoModelFactory):
    """Factory for creating sponsored student relationships."""

    class Meta:
        model = SponsoredStudent

    sponsor = SubFactory(SponsorFactory)

    # Reference to student from people app
    student = factory.LazyAttribute(lambda obj: None)  # Will be set in tests

    sponsorship_type = Faker(
        "random_element",
        elements=[
            SponsoredStudent.SponsorshipType.FULL,
            SponsoredStudent.SponsorshipType.FULL,  # Weight toward full sponsorship
            SponsoredStudent.SponsorshipType.PARTIAL,
            SponsoredStudent.SponsorshipType.SCHOLARSHIP,
            SponsoredStudent.SponsorshipType.EMERGENCY,
        ],
    )

    # Date ranges - typically start at beginning of academic terms
    start_date = Faker("date_between", start_date="-1y", end_date="today")
    end_date = factory.LazyAttribute(
        lambda obj: obj.start_date + timedelta(days=730),  # 2 years
    )

    notes = factory.LazyAttribute(
        lambda obj: (
            f"{obj.sponsorship_type.replace('_', ' ').title()} sponsorship arrangement"
            f" starting {obj.start_date.strftime('%B %Y')}"
            if Faker("boolean", chance_of_getting_true=30)
            else ""
        ),
    )


class ScholarshipFactory(DjangoModelFactory):
    """Factory for creating scholarships."""

    class Meta:
        model = Scholarship

    name = Faker("random_element", elements=MERIT_SCHOLARSHIP_TYPES)

    scholarship_type = Faker(
        "random_element",
        elements=[
            Scholarship.ScholarshipType.MERIT,
            Scholarship.ScholarshipType.MERIT,  # Weight toward merit-based
            Scholarship.ScholarshipType.NEED,
            Scholarship.ScholarshipType.SPONSORED,
            Scholarship.ScholarshipType.ACADEMIC,
            Scholarship.ScholarshipType.EMERGENCY,
            Scholarship.ScholarshipType.ATHLETIC,
        ],
    )

    sponsored_student = SubFactory(SponsoredStudentFactory)

    # Award structure - either percentage or fixed amount using constants
    award_percentage = Faker(
        "random_element",
        elements=[
            STANDARD_DISCOUNTS["FULL_SPONSORSHIP"],
            STANDARD_DISCOUNTS["PARTIAL_75"],
            STANDARD_DISCOUNTS["PARTIAL_50"],
            STANDARD_DISCOUNTS["PARTIAL_25"],
            Decimal("10.00"),
        ],
    )

    award_amount = None

    # Validity period
    start_date = Faker("date_between", start_date="-6m", end_date="today")
    end_date = factory.LazyAttribute(
        lambda obj: obj.start_date + timedelta(days=730),  # 2 years
    )

    status = Faker(
        "random_element",
        elements=[
            Scholarship.AwardStatus.ACTIVE,
            Scholarship.AwardStatus.ACTIVE,  # Weight toward active
            Scholarship.AwardStatus.APPROVED,
            Scholarship.AwardStatus.PENDING,
            Scholarship.AwardStatus.SUSPENDED,
            Scholarship.AwardStatus.COMPLETED,
        ],
    )

    description = factory.LazyAttribute(
        lambda obj: f"This {obj.scholarship_type.lower().replace('_', '-')} scholarship "
        f"recognizes outstanding {obj.scholarship_type.lower().replace('_', ' ')} achievement "
        f"and provides financial support for educational expenses.",
    )

    conditions = factory.LazyAttribute(
        lambda obj: (
            f"Maintain minimum GPA of 3.0, demonstrate continued "
            f"{obj.scholarship_type.lower().replace('_', ' ')} excellence, "
            f"and submit progress reports each semester."
            if obj.scholarship_type in [Scholarship.ScholarshipType.MERIT, Scholarship.ScholarshipType.ACADEMIC]
            else "Meet financial need criteria and maintain academic standing."
        ),
    )

    notes = factory.LazyAttribute(
        lambda obj: (
            f"Scholarship awarded for {obj.start_date.year} academic year"
            if Faker("boolean", chance_of_getting_true=25)
            else ""
        ),
    )


class IndependentScholarshipFactory(ScholarshipFactory):
    """Factory for scholarships not linked to sponsors."""

    sponsored_student = None

    scholarship_type = Faker(
        "random_element",
        elements=[
            Scholarship.ScholarshipType.MERIT,
            Scholarship.ScholarshipType.NEED,
            Scholarship.ScholarshipType.ACADEMIC,
            Scholarship.ScholarshipType.ATHLETIC,
            Scholarship.ScholarshipType.EMERGENCY,
        ],
    )


# Utility factory for creating complete scholarship scenarios
class ScholarshipScenarioFactory:
    """Factory for creating complete scholarship scenarios with related data."""

    @classmethod
    def create_sponsored_scholarship_program(cls, sponsor_code="CRST", num_students=10):
        """Create a complete sponsored scholarship program."""
        # Create sponsor organization
        sponsor = SponsorFactory(
            code=sponsor_code,
            default_discount_percentage=Decimal("100.00"),  # Full sponsorship
            requests_consolidated_invoicing=True,
            requests_attendance_reporting=True,
            requests_grade_reporting=True,
        )

        scholarships = []
        sponsored_students = []

        for _i in range(num_students):
            # Create sponsored student relationship
            sponsored_student = SponsoredStudentFactory(
                sponsor=sponsor,
                sponsorship_type=SponsoredStudent.SponsorshipType.FULL,
                start_date=timezone.now().date().replace(month=1, day=1),  # Start of academic year
            )
            sponsored_students.append(sponsored_student)

            # Create associated scholarship
            scholarship = ScholarshipFactory(
                name=f"{sponsor.name} Full Scholarship",
                scholarship_type=Scholarship.ScholarshipType.SPONSORED,
                sponsored_student=sponsored_student,
                award_percentage=Decimal("100.00"),
                award_amount=None,
                status=Scholarship.AwardStatus.ACTIVE,
                start_date=sponsored_student.start_date,
            )
            scholarships.append(scholarship)

        return {
            "sponsor": sponsor,
            "sponsored_students": sponsored_students,
            "scholarships": scholarships,
        }

    @classmethod
    def create_merit_scholarship_program(cls, num_recipients=5):
        """Create a merit-based scholarship program."""
        scholarships = []

        merit_types = [
            ("Academic Excellence Award", Decimal("75.00")),
            ("Outstanding Achievement Scholarship", Decimal("50.00")),
            ("Leadership Development Award", Decimal("25.00")),
            ("Community Service Scholarship", Decimal("25.00")),
            ("Innovation Award", Decimal("100.00")),
        ]

        for i in range(num_recipients):
            name, percentage = merit_types[i % len(merit_types)]

            scholarship = IndependentScholarshipFactory(
                name=name,
                scholarship_type=Scholarship.ScholarshipType.MERIT,
                award_percentage=percentage,
                award_amount=None,
                status=Scholarship.AwardStatus.ACTIVE,
                conditions="Maintain minimum GPA of 3.5, participate in community service, "
                "and demonstrate continued academic excellence.",
            )
            scholarships.append(scholarship)

        return scholarships

    @classmethod
    def create_need_based_aid_program(cls, num_recipients=8):
        """Create a need-based financial aid program."""
        scholarships = []

        aid_amounts = [
            Decimal("1000.00"),
            Decimal("1500.00"),
            Decimal("2000.00"),
            Decimal("2500.00"),
            Decimal("3000.00"),
        ]

        for i in range(num_recipients):
            amount = aid_amounts[i % len(aid_amounts)]

            scholarship = IndependentScholarshipFactory(
                name="Need-Based Financial Aid",
                scholarship_type=Scholarship.ScholarshipType.NEED,
                award_percentage=None,
                award_amount=amount,
                status=Scholarship.AwardStatus.ACTIVE,
                conditions="Demonstrate financial need, maintain academic standing, "
                "and submit financial documentation annually.",
                description="Financial aid for students demonstrating significant "
                "financial need and academic potential.",
            )
            scholarships.append(scholarship)

        return scholarships

    @classmethod
    def create_comprehensive_scholarship_system(cls):
        """Create a comprehensive scholarship system with multiple programs."""
        # Create sponsored programs
        crst_program = cls.create_sponsored_scholarship_program("CRST", 15)
        plf_program = cls.create_sponsored_scholarship_program("PLF", 12)
        usaid_program = cls.create_sponsored_scholarship_program("USAID", 8)

        # Create merit-based scholarships
        merit_scholarships = cls.create_merit_scholarship_program(10)

        # Create need-based aid
        need_based_aid = cls.create_need_based_aid_program(20)

        # Create emergency aid scholarships
        emergency_scholarships = []
        for _i in range(5):
            scholarship = IndependentScholarshipFactory(
                name="Emergency Financial Support",
                scholarship_type=Scholarship.ScholarshipType.EMERGENCY,
                award_amount=Faker(
                    "random_element",
                    elements=[Decimal("200.00"), Decimal("500.00"), Decimal("1000.00")],
                ),
                award_percentage=None,
                status=Scholarship.AwardStatus.ACTIVE,
                start_date=Faker("date_between", start_date="-30d", end_date="today"),
                end_date=None,  # Emergency aid is typically short-term but flexible
                conditions="Demonstrate urgent financial need and maintain enrollment.",
                description="Short-term emergency financial support for students "
                "facing unexpected financial hardships.",
            )
            emergency_scholarships.append(scholarship)

        return {
            "sponsored_programs": {
                "crst": crst_program,
                "plf": plf_program,
                "usaid": usaid_program,
            },
            "merit_scholarships": merit_scholarships,
            "need_based_aid": need_based_aid,
            "emergency_scholarships": emergency_scholarships,
            "total_scholarships": (
                len(crst_program["scholarships"])
                + len(plf_program["scholarships"])
                + len(usaid_program["scholarships"])
                + len(merit_scholarships)
                + len(need_based_aid)
                + len(emergency_scholarships)
            ),
        }


class SponsorManagementScenarioFactory:
    """Factory for creating sponsor management scenarios."""

    @classmethod
    def create_multi_sponsor_scenario(cls):
        """Create multiple sponsors with different characteristics."""
        sponsors = []

        # Large international sponsor with full coverage
        international_sponsor = SponsorFactory(
            code="USAID",
            name="United States Agency for International Development",
            default_discount_percentage=Decimal("100.00"),
            requests_consolidated_invoicing=True,
            requests_attendance_reporting=True,
            requests_grade_reporting=True,
            mou_start_date=timezone.now().date().replace(year=timezone.now().date().year - 2),
            mou_end_date=timezone.now().date().replace(year=timezone.now().date().year + 3),
        )
        sponsors.append(international_sponsor)

        # Regional sponsor with partial coverage
        regional_sponsor = SponsorFactory(
            code="KOICA",
            name="Korea International Cooperation Agency",
            default_discount_percentage=Decimal("75.00"),
            requests_consolidated_invoicing=False,
            requests_attendance_reporting=True,
            requests_grade_reporting=False,
        )
        sponsors.append(regional_sponsor)

        # Local foundation with specific focus
        local_sponsor = SponsorFactory(
            code="PLF",
            name="Presbyterian Leadership Foundation",
            default_discount_percentage=Decimal("50.00"),
            requests_consolidated_invoicing=True,
            requests_attendance_reporting=True,
            requests_grade_reporting=True,
            admin_fee_exempt_until=timezone.now().date().replace(year=timezone.now().date().year + 1),
        )
        sponsors.append(local_sponsor)

        return sponsors

    @classmethod
    def create_sponsor_with_students(cls, sponsor_code="CRST", num_students=5):
        """Create a sponsor with multiple sponsored students."""
        sponsor = SponsorFactory(code=sponsor_code)

        sponsored_students = []
        for _i in range(num_students):
            sponsored_student = SponsoredStudentFactory(
                sponsor=sponsor,
                sponsorship_type=Faker(
                    "random_element",
                    elements=[
                        SponsoredStudent.SponsorshipType.FULL,
                        SponsoredStudent.SponsorshipType.PARTIAL,
                        SponsoredStudent.SponsorshipType.SCHOLARSHIP,
                    ],
                ),
            )
            sponsored_students.append(sponsored_student)

        return {"sponsor": sponsor, "sponsored_students": sponsored_students}
