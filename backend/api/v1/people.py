"""People API endpoints for managing students, teachers, staff, and persons.

This module provides RESTful API endpoints for React queries to access and
manage people data including students, teachers, staff, contacts, and related
information.
"""


from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router

from apps.enrollment.models import MajorDeclaration
from apps.people.models import (
    EmergencyContact,
    Person,
    StaffProfile,
    StudentProfile,
    TeacherProfile,
)

from .auth import jwt_auth
from .people_schemas import (
    EmergencyContactSchema,
    PaginatedSearchResultsSchema,
    PaginatedStaffSchema,
    PaginatedStudentsSchema,
    PaginatedTeachersSchema,
    PersonDetailSchema,
    PhoneNumberSchema,
)

router = Router(auth=jwt_auth, tags=["people"])


# Helper functions for data serialization
def serialize_person_detail(person: Person) -> dict:
    """Serialize complete person details."""
    data = {
        "unique_id": str(person.unique_id),
        "family_name": person.family_name,
        "personal_name": person.personal_name,
        "full_name": person.full_name,
        "khmer_name": person.khmer_name,
        "preferred_gender": person.preferred_gender,
        "school_email": person.school_email,
        "personal_email": person.personal_email,
        "date_of_birth": person.date_of_birth,
        "birth_province": person.birth_province,
        "citizenship": str(person.citizenship),
        "age": person.age,
        "display_name": person.display_name,
        "current_photo_url": person.current_photo_url,
        "current_thumbnail_url": person.current_thumbnail_url,
        "has_student_role": person.has_student_role,
        "has_teacher_role": person.has_teacher_role,
        "has_staff_role": person.has_staff_role,
    }

    # Add profiles if they exist
    if person.has_student_role:
        student = person.student_profile
        declared_major = student.declared_major
        enrollment_major = student.enrollment_history_major

        data["student_profile"] = {
            "id": student.id,
            "student_id": student.student_id,
            "formatted_student_id": student.formatted_student_id,
            "legacy_ipk": student.legacy_ipk,
            "is_monk": student.is_monk,
            "is_transfer_student": student.is_transfer_student,
            "current_status": student.current_status,
            "study_time_preference": student.study_time_preference,
            "last_enrollment_date": student.last_enrollment_date,
            "is_student_active": student.is_student_active,
            "has_major_conflict": student.has_major_conflict,
            "declared_major_name": declared_major.name if declared_major else None,
            "enrollment_history_major_name": enrollment_major.name if enrollment_major else None,
        }

    if person.has_teacher_role:
        teacher = person.teacher_profile
        data["teacher_profile"] = {
            "id": teacher.id,
            "terminal_degree": teacher.terminal_degree,
            "status": teacher.status,
            "start_date": teacher.start_date,
            "end_date": teacher.end_date,
            "is_teacher_active": teacher.is_teacher_active,
        }

    if person.has_staff_role:
        staff = person.staff_profile
        data["staff_profile"] = {
            "id": staff.id,
            "position": staff.position,
            "status": staff.status,
            "start_date": staff.start_date,
            "end_date": staff.end_date,
            "is_staff_active": staff.is_staff_active,
        }

    # Add contact information
    data["phone_numbers"] = [
        {
            "id": phone.id,
            "number": phone.number,
            "comment": phone.comment,
            "is_preferred": phone.is_preferred,
            "is_telegram": phone.is_telegram,
            "is_verified": phone.is_verified,
        }
        for phone in person.phone_numbers.all()
    ]

    data["emergency_contacts"] = [
        {
            "id": contact.id,
            "name": contact.name,
            "relationship": contact.relationship,
            "primary_phone": contact.primary_phone,
            "secondary_phone": contact.secondary_phone,
            "email": contact.email,
            "address": contact.address,
            "is_primary": contact.is_primary,
        }
        for contact in person.emergency_contacts.all()
    ]

    return data


def serialize_student_list(student: StudentProfile) -> dict:
    """Serialize student for list view."""
    person = student.person
    declared_major = student.declared_major

    return {
        "person_id": person.id,
        "student_id": student.student_id,
        "formatted_student_id": student.formatted_student_id,
        "full_name": person.full_name,
        "khmer_name": person.khmer_name,
        "school_email": person.school_email,
        "current_status": student.current_status,
        "study_time_preference": student.study_time_preference,
        "is_monk": student.is_monk,
        "current_thumbnail_url": person.current_thumbnail_url,
        "declared_major_name": declared_major.name if declared_major else None,
    }


# Person endpoints
@router.get("/persons/{person_id}/", response=PersonDetailSchema)
def get_person(request, person_id: int):
    """Get detailed person information by ID."""
    person = get_object_or_404(
        Person.objects.select_related("student_profile", "teacher_profile", "staff_profile")
        .prefetch_related("phone_numbers", "emergency_contacts")
        .prefetch_related(
            Prefetch(
                "student_profile__majordeclaration_set",
                queryset=MajorDeclaration.objects.select_related("major").filter(is_active=True),
            )
        ),
        id=person_id,
    )
    return serialize_person_detail(person)


@router.get("/persons/search/", response=PaginatedSearchResultsSchema)
def search_persons(
    request,
    q: str = Query(..., description="Search query"),
    roles: list[str] | None = Query(None, description="Filter by roles: student, teacher, staff"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Search for persons across all roles."""
    queryset = Person.objects.select_related("student_profile", "teacher_profile", "staff_profile").distinct()

    # Apply text search
    if q:
        queryset = queryset.filter(
            Q(full_name__icontains=q)
            | Q(khmer_name__icontains=q)
            | Q(school_email__icontains=q)
            | Q(student_profile__student_id__icontains=q)
        )

    # Apply role filters
    if roles:
        role_filters = Q()
        if "student" in roles:
            role_filters |= Q(student_profile__isnull=False)
        if "teacher" in roles:
            role_filters |= Q(teacher_profile__isnull=False)
        if "staff" in roles:
            role_filters |= Q(staff_profile__isnull=False)
        queryset = queryset.filter(role_filters)

    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    # Serialize results
    results = []
    for person in page_obj:
        person_roles = []
        if person.has_student_role:
            person_roles.append("student")
        if person.has_teacher_role:
            person_roles.append("teacher")
        if person.has_staff_role:
            person_roles.append("staff")

        result = {
            "person_id": person.id,
            "full_name": person.full_name,
            "khmer_name": person.khmer_name,
            "school_email": person.school_email,
            "current_thumbnail_url": person.current_thumbnail_url,
            "roles": person_roles,
        }

        # Add role-specific info
        if person.has_student_role:
            student = person.student_profile
            result["student_id"] = student.student_id
            result["formatted_student_id"] = student.formatted_student_id
            result["student_status"] = student.current_status

        if person.has_teacher_role:
            result["teacher_status"] = person.teacher_profile.status

        if person.has_staff_role:
            result["position"] = person.staff_profile.position

        results.append(result)

    return {
        "count": paginator.count,
        "next": None,  # Simplified - could add full URL construction
        "previous": None,
        "results": results,
    }


# Student endpoints
@router.get("/students/", response=PaginatedStudentsSchema)
def list_students(
    request,
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search students"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List students with optional filtering."""
    queryset = StudentProfile.objects.select_related("person").prefetch_related(
        Prefetch(
            "majordeclaration_set", queryset=MajorDeclaration.objects.select_related("major").filter(is_active=True)
        )
    )

    if status:
        queryset = queryset.filter(current_status=status)

    if search:
        queryset = queryset.filter(
            Q(person__full_name__icontains=search)
            | Q(person__khmer_name__icontains=search)
            | Q(student_id__icontains=search)
            | Q(person__school_email__icontains=search)
        )

    queryset = queryset.order_by("student_id")

    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    results = [serialize_student_list(student) for student in page_obj]

    return {"count": paginator.count, "next": None, "previous": None, "results": results}


@router.get("/students/{student_id}/", response=PersonDetailSchema)
def get_student_by_id(request, student_id: int):
    """Get student details by student ID."""
    student = get_object_or_404(
        StudentProfile.objects.select_related("person").prefetch_related(
            "person__phone_numbers", "person__emergency_contacts"
        ),
        student_id=student_id,
    )
    return serialize_person_detail(student.person)


# Teacher endpoints
@router.get("/teachers/", response=PaginatedTeachersSchema)
def list_teachers(
    request,
    status: str | None = Query(None, description="Filter by status"),
    active_only: bool = Query(False, description="Show only active teachers"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List teachers with optional filtering."""
    queryset = TeacherProfile.objects.select_related("person")

    if status:
        queryset = queryset.filter(status=status)

    if active_only:
        queryset = queryset.filter(status="ACTIVE")

    queryset = queryset.order_by("person__family_name", "person__personal_name")

    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    results = [
        {
            "person_id": teacher.person.id,
            "full_name": teacher.person.full_name,
            "khmer_name": teacher.person.khmer_name,
            "school_email": teacher.person.school_email,
            "terminal_degree": teacher.terminal_degree,
            "status": teacher.status,
            "is_teacher_active": teacher.is_teacher_active,
            "current_thumbnail_url": teacher.person.current_thumbnail_url,
        }
        for teacher in page_obj
    ]

    return {"count": paginator.count, "next": None, "previous": None, "results": results}


# Staff endpoints
@router.get("/staff/", response=PaginatedStaffSchema)
def list_staff(
    request,
    status: str | None = Query(None, description="Filter by status"),
    active_only: bool = Query(False, description="Show only active staff"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List staff with optional filtering."""
    queryset = StaffProfile.objects.select_related("person")

    if status:
        queryset = queryset.filter(status=status)

    if active_only:
        queryset = queryset.filter(status="ACTIVE")

    queryset = queryset.order_by("person__family_name", "person__personal_name")

    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    results = [
        {
            "person_id": staff.person.id,
            "full_name": staff.person.full_name,
            "khmer_name": staff.person.khmer_name,
            "school_email": staff.person.school_email,
            "position": staff.position,
            "status": staff.status,
            "is_staff_active": staff.is_staff_active,
            "current_thumbnail_url": staff.person.current_thumbnail_url,
        }
        for staff in page_obj
    ]

    return {"count": paginator.count, "next": None, "previous": None, "results": results}


# Contact information endpoints
@router.get("/persons/{person_id}/phone-numbers/", response=list[PhoneNumberSchema])
def get_person_phone_numbers(request, person_id: int):
    """Get all phone numbers for a person."""
    person = get_object_or_404(Person, id=person_id)
    phone_numbers = person.phone_numbers.all().order_by("-is_preferred", "number")

    return [
        {
            "id": phone.id,
            "number": phone.number,
            "comment": phone.comment,
            "is_preferred": phone.is_preferred,
            "is_telegram": phone.is_telegram,
            "is_verified": phone.is_verified,
        }
        for phone in phone_numbers
    ]


@router.get("/persons/{person_id}/emergency-contacts/", response=list[EmergencyContactSchema])
def get_person_emergency_contacts(request, person_id: int):
    """Get all emergency contacts for a person."""
    person = get_object_or_404(Person, id=person_id)
    contacts = person.emergency_contacts.all().order_by("-is_primary", "name")

    return [
        {
            "id": contact.id,
            "name": contact.name,
            "relationship": contact.relationship,
            "primary_phone": contact.primary_phone,
            "secondary_phone": contact.secondary_phone,
            "email": contact.email,
            "address": contact.address,
            "is_primary": contact.is_primary,
        }
        for contact in contacts
    ]


# Utility endpoints for React forms/dropdowns
@router.get("/students/statuses/", response=list[dict])
def get_student_statuses(request):
    """Get all available student status choices."""
    return [{"value": choice[0], "label": choice[1]} for choice in StudentProfile.Status.choices]


@router.get("/teachers/statuses/", response=list[dict])
def get_teacher_statuses(request):
    """Get all available teacher status choices."""
    return [{"value": choice[0], "label": choice[1]} for choice in TeacherProfile.Status.choices]


@router.get("/staff/statuses/", response=list[dict])
def get_staff_statuses(request):
    """Get all available staff status choices."""
    return [{"value": choice[0], "label": choice[1]} for choice in StaffProfile.Status.choices]


@router.get("/emergency-contacts/relationships/", response=list[dict])
def get_relationship_choices(request):
    """Get all available emergency contact relationship choices."""

    return [{"value": choice[0], "label": choice[1]} for choice in EmergencyContact.Relationship.choices]
