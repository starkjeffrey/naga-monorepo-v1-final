"""Factory definitions for all models using factory_boy.

These factories provide a consistent way to generate test data across
all tests. They handle relationships and generate realistic data.
"""

from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from faker import Faker

from apps.curriculum.models import (
    Course,
    Division,
    Major,  # Changed from Program to Major
    Term,
)
from apps.people.models import EmergencyContact, Person, StaffProfile, StudentProfile, TeacherProfile
from apps.scheduling.models import ClassHeader, ClassPart, Room

# Import all models
from users.models import User

fake = Faker()

# --- User and Authentication Factories ---


class UserFactory(DjangoModelFactory):
    """Factory for User model."""

    class Meta:
        model = User
        django_get_or_create = ["email"]

    email = factory.LazyAttribute(lambda o: fake.unique.email())
    first_name = factory.LazyAttribute(lambda o: fake.first_name())
    last_name = factory.LazyAttribute(lambda o: fake.last_name())
    is_active = True
    is_staff = False
    is_superuser = False
    date_joined = factory.LazyFunction(timezone.now)

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.set_password(extracted)
        else:
            self.set_password("testpass123")

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for group in extracted:
                self.groups.add(group)


class StaffUserFactory(UserFactory):
    """Factory for staff users."""

    is_staff = True


class AdminUserFactory(UserFactory):
    """Factory for admin users."""

    is_staff = True
    is_superuser = True


# --- People Factories ---


class PersonFactory(DjangoModelFactory):
    """Factory for Person model."""

    class Meta:
        model = Person
        django_get_or_create = ["personal_email"]

    personal_name = factory.LazyAttribute(lambda o: fake.first_name())
    family_name = factory.LazyAttribute(lambda o: fake.last_name())
    middle_name = factory.LazyAttribute(
        lambda o: fake.first_name() if fake.boolean(chance_of_getting_true=30) else None
    )
    preferred_name = factory.LazyAttribute(
        lambda o: o.personal_name if fake.boolean(chance_of_getting_true=70) else fake.first_name()
    )

    date_of_birth = factory.LazyAttribute(lambda o: fake.date_of_birth(minimum_age=18, maximum_age=65))
    place_of_birth = factory.LazyAttribute(lambda o: fake.city())

    preferred_gender = factory.LazyAttribute(lambda o: fake.random_element(["M", "F", "O"]))
    citizenship = factory.LazyAttribute(lambda o: fake.country_code())
    passport_number = factory.LazyAttribute(lambda o: fake.bothify("??######"))
    national_id = factory.LazyAttribute(lambda o: fake.bothify("###########"))

    personal_email = factory.LazyAttribute(lambda o: fake.unique.email())
    university_email = factory.LazyAttribute(
        lambda o: f"{o.personal_name.lower()}.{o.family_name.lower()}@pucsr.edu.kh"
    )
    phone_number = factory.LazyAttribute(lambda o: fake.phone_number())
    emergency_phone = factory.LazyAttribute(lambda o: fake.phone_number())

    current_address = factory.LazyAttribute(lambda o: fake.address())
    permanent_address = factory.LazyAttribute(lambda o: fake.address())

    profile_photo = None
    is_active = True
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class StudentProfileFactory(DjangoModelFactory):
    """Factory for StudentProfile model."""

    class Meta:
        model = StudentProfile
        django_get_or_create = ["student_id"]

    person = factory.SubFactory(PersonFactory)
    student_id = factory.Sequence(lambda n: 20240000 + n)

    entry_date = factory.LazyAttribute(lambda o: fake.date_between(start_date="-2y", end_date="today"))
    expected_graduation_date = factory.LazyAttribute(lambda o: o.entry_date + timedelta(days=365 * 4))
    actual_graduation_date = None

    last_enrollment_date = factory.LazyAttribute(
        lambda o: fake.date_between(start_date=o.entry_date, end_date="today")
    )
    current_status = factory.LazyAttribute(
        lambda o: fake.random_element(["ACTIVE", "INACTIVE", "GRADUATED", "WITHDRAWN"])
    )

    high_school = factory.LazyAttribute(lambda o: fake.company())
    high_school_graduation_year = factory.LazyAttribute(lambda o: o.entry_date.year - 1)

    guardian_name = factory.LazyAttribute(lambda o: fake.name())
    guardian_relationship = factory.LazyAttribute(lambda o: fake.random_element(["Parent", "Guardian", "Relative"]))
    guardian_phone = factory.LazyAttribute(lambda o: fake.phone_number())
    guardian_email = factory.LazyAttribute(lambda o: fake.email())

    medical_conditions = factory.LazyAttribute(
        lambda o: fake.text(max_nb_chars=200) if fake.boolean(chance_of_getting_true=20) else None
    )
    dietary_restrictions = factory.LazyAttribute(
        lambda o: fake.random_element(["None", "Vegetarian", "Vegan", "Halal", "Kosher"])
    )

    notes = factory.LazyAttribute(
        lambda o: fake.text(max_nb_chars=500) if fake.boolean(chance_of_getting_true=30) else None
    )


class TeacherProfileFactory(DjangoModelFactory):
    """Factory for TeacherProfile model."""

    class Meta:
        model = TeacherProfile
        django_get_or_create = ["employee_id"]

    person = factory.SubFactory(PersonFactory)
    employee_id = factory.Sequence(lambda n: f"TCH{2024000 + n}")

    hire_date = factory.LazyAttribute(lambda o: fake.date_between(start_date="-5y", end_date="today"))
    contract_type = factory.LazyAttribute(lambda o: fake.random_element(["FULL_TIME", "PART_TIME", "ADJUNCT"]))

    department = factory.LazyAttribute(
        lambda o: fake.random_element(["Computer Science", "Mathematics", "Physics", "English"])
    )
    title = factory.LazyAttribute(
        lambda o: fake.random_element(["Instructor", "Assistant Professor", "Associate Professor", "Professor"])
    )

    office_location = factory.LazyAttribute(
        lambda o: f"Building {fake.random_letter()} Room {fake.random_int(100, 500)}"
    )
    office_hours = factory.LazyAttribute(lambda o: f"MWF {fake.random_int(9, 16)}:00-{fake.random_int(10, 17)}:00")

    qualifications = factory.LazyAttribute(lambda o: fake.text(max_nb_chars=500))
    specializations = factory.LazyAttribute(lambda o: ", ".join(fake.words(nb=3)))

    is_active = True
    can_supervise_projects = factory.LazyAttribute(lambda o: fake.boolean(chance_of_getting_true=70))


class StaffProfileFactory(DjangoModelFactory):
    """Factory for StaffProfile model."""

    class Meta:
        model = StaffProfile

    person = factory.SubFactory(PersonFactory)
    employee_id = factory.Sequence(lambda n: f"STF{2024000 + n}")

    hire_date = factory.LazyAttribute(lambda o: fake.date_between(start_date="-5y", end_date="today"))
    department = factory.LazyAttribute(
        lambda o: fake.random_element(["Administration", "Finance", "IT", "Library", "Student Services"])
    )
    position = factory.LazyAttribute(lambda o: fake.job())

    supervisor = factory.SubFactory("tests.fixtures.factories.StaffProfileFactory", supervisor=None)
    is_active = True


class EmergencyContactFactory(DjangoModelFactory):
    """Factory for EmergencyContact model."""

    class Meta:
        model = EmergencyContact

    person = factory.SubFactory(PersonFactory)

    name = factory.LazyAttribute(lambda o: fake.name())
    relationship = factory.LazyAttribute(lambda o: fake.random_element(["Parent", "Spouse", "Sibling", "Friend"]))
    phone_primary = factory.LazyAttribute(lambda o: fake.phone_number())
    phone_secondary = factory.LazyAttribute(
        lambda o: fake.phone_number() if fake.boolean(chance_of_getting_true=50) else None
    )
    email = factory.LazyAttribute(lambda o: fake.email())
    address = factory.LazyAttribute(lambda o: fake.address())

    is_primary = True
    priority_order = 1


# --- Curriculum Factories ---


class DivisionFactory(DjangoModelFactory):
    """Factory for Division model."""

    class Meta:
        model = Division
        django_get_or_create = ["short_name"]

    name = factory.LazyAttribute(
        lambda o: fake.random_element(["Computer Science", "Mathematics", "Physics", "English", "Business"])
    )
    short_name = factory.LazyAttribute(lambda o: "".join([word[0] for word in o.name.split()]).upper())
    description = factory.LazyAttribute(lambda o: fake.text(max_nb_chars=200))
    is_active = True


class CourseFactory(DjangoModelFactory):
    """Factory for Course model."""

    class Meta:
        model = Course
        django_get_or_create = ["code"]

    code = factory.LazyAttribute(
        lambda o: f"{fake.random_element(['CS', 'MATH', 'PHYS', 'ENG', 'BUS'])}{fake.random_int(100, 499)}"
    )
    title = factory.LazyAttribute(lambda o: fake.catch_phrase())
    short_title = factory.LazyAttribute(lambda o: " ".join(o.title.split()[:2]))

    credits = factory.LazyAttribute(lambda o: fake.random_element([1, 2, 3, 4]))
    division = factory.SubFactory(DivisionFactory)

    cycle = factory.LazyAttribute(lambda o: fake.random_element(["BA", "AA", "CERT"]))
    level = factory.LazyAttribute(lambda o: fake.random_element(["100", "200", "300", "400"]))

    description = factory.LazyAttribute(lambda o: fake.text(max_nb_chars=500))
    objectives = factory.LazyAttribute(lambda o: fake.text(max_nb_chars=300))

    is_active = True
    is_elective = factory.LazyAttribute(lambda o: fake.boolean(chance_of_getting_true=30))
    has_lab = factory.LazyAttribute(lambda o: fake.boolean(chance_of_getting_true=20))
    has_tutorial = factory.LazyAttribute(lambda o: fake.boolean(chance_of_getting_true=15))


class TermFactory(DjangoModelFactory):
    """Factory for Term model."""

    class Meta:
        model = Term
        django_get_or_create = ["code"]

    name = factory.LazyAttribute(
        lambda o: f"{fake.random_element(['Fall', 'Spring', 'Summer'])} {fake.random_int(2024, 2025)}"
    )
    code = factory.LazyAttribute(lambda o: f"{o.name.split()[0][:2].upper()}{o.name.split()[1]}")

    start_date = factory.LazyAttribute(lambda o: fake.date_between(start_date="today", end_date="+3m"))
    end_date = factory.LazyAttribute(lambda o: o.start_date + timedelta(days=120))

    registration_start = factory.LazyAttribute(lambda o: o.start_date - timedelta(days=30))
    registration_end = factory.LazyAttribute(lambda o: o.start_date + timedelta(days=7))

    drop_deadline = factory.LazyAttribute(lambda o: o.start_date + timedelta(days=14))
    withdraw_deadline = factory.LazyAttribute(lambda o: o.start_date + timedelta(days=60))

    is_active = True
    is_current = False


class MajorFactory(DjangoModelFactory):
    """Factory for Major model."""

    class Meta:
        model = Major
        django_get_or_create = ["code"]

    name = factory.LazyAttribute(
        lambda o: f"Bachelor of {fake.random_element(['Science', 'Arts', 'Business'])} in {fake.job()}"
    )
    code = factory.LazyAttribute(
        lambda o: "".join([word[0] for word in o.name.split() if word not in ["of", "in"]]).upper()
    )

    degree_type = factory.LazyAttribute(lambda o: fake.random_element(["BA", "BS", "AA", "AS"]))
    division = factory.SubFactory(DivisionFactory)

    total_credits = factory.LazyAttribute(lambda o: fake.random_element([120, 128, 132]))
    duration_years = 4

    description = factory.LazyAttribute(lambda o: fake.text(max_nb_chars=500))
    learning_outcomes = factory.LazyAttribute(lambda o: fake.text(max_nb_chars=400))

    is_active = True
    requires_senior_project = factory.LazyAttribute(lambda o: fake.boolean(chance_of_getting_true=70))
    requires_internship = factory.LazyAttribute(lambda o: fake.boolean(chance_of_getting_true=50))


# --- Scheduling Factories ---


class RoomFactory(DjangoModelFactory):
    """Factory for Room model."""

    class Meta:
        model = Room
        django_get_or_create = ["room_number"]

    building = factory.LazyAttribute(lambda o: fake.random_element(["Main", "Science", "Library", "Admin"]))
    room_number = factory.LazyAttribute(lambda o: f"{o.building[0]}{fake.random_int(100, 499)}")

    capacity = factory.LazyAttribute(lambda o: fake.random_element([20, 30, 40, 50, 100]))
    room_type = factory.LazyAttribute(lambda o: fake.random_element(["CLASSROOM", "LAB", "LECTURE_HALL", "SEMINAR"]))

    has_projector = factory.LazyAttribute(lambda o: fake.boolean(chance_of_getting_true=80))
    has_whiteboard = True
    has_computers = factory.LazyAttribute(lambda o: o.room_type == "LAB")

    is_active = True


class ClassHeaderFactory(DjangoModelFactory):
    """Factory for ClassHeader model."""

    class Meta:
        model = ClassHeader

    course = factory.SubFactory(CourseFactory)
    term = factory.SubFactory(TermFactory)

    section = factory.Sequence(lambda n: chr(65 + n % 26))  # A, B, C, etc.
    crn = factory.Sequence(lambda n: 10000 + n)

    max_enrollment = factory.LazyAttribute(lambda o: fake.random_element([20, 30, 40]))
    current_enrollment = 0
    waitlist_capacity = factory.LazyAttribute(lambda o: int(o.max_enrollment * 0.2))

    instruction_mode = factory.LazyAttribute(lambda o: fake.random_element(["IN_PERSON", "ONLINE", "HYBRID"]))
    instruction_language = factory.LazyAttribute(lambda o: fake.random_element(["EN", "KH", "BILINGUAL"]))

    is_active = True
    allow_waitlist = True


class ClassPartFactory(DjangoModelFactory):
    """Factory for ClassPart model."""

    class Meta:
        model = ClassPart

    class_header = factory.SubFactory(ClassHeaderFactory)
    part_type = factory.LazyAttribute(lambda o: fake.random_element(["LECTURE", "LAB", "TUTORIAL"]))

    teacher = factory.SubFactory(TeacherProfileFactory)
    room = factory.SubFactory(RoomFactory)

    day_of_week = factory.LazyAttribute(lambda o: fake.random_element([1, 2, 3, 4, 5]))  # Monday to Friday
    start_time = factory.LazyAttribute(lambda o: fake.random_element(["08:00", "09:30", "11:00", "13:30", "15:00"]))
    end_time = factory.LazyAttribute(
        lambda o: {"08:00": "09:20", "09:30": "10:50", "11:00": "12:20", "13:30": "14:50", "15:00": "16:20"}[
            o.start_time
        ]
    )

    is_active = True


# --- Continue with more factories in next part ---
