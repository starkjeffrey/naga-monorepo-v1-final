"""Factory-boy factories for attendance models.

This module provides factory classes for generating realistic test data
for attendance tracking models including:
- Attendance settings and sessions
- Student attendance records
- Permission requests and roster syncing
- Attendance archival

Following clean architecture principles with realistic data generation
that supports comprehensive testing of attendance workflows.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import factory
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

from apps.attendance.models import (
    AttendanceArchive,
    AttendanceRecord,
    AttendanceSession,
    AttendanceSettings,
    PermissionRequest,
    RosterSync,
)


class AttendanceSettingsFactory(DjangoModelFactory):
    """Factory for creating attendance settings."""

    class Meta:
        model = AttendanceSettings

    allows_permission_requests = Faker("boolean", chance_of_getting_true=80)
    auto_approve_permissions = Faker("boolean", chance_of_getting_true=30)
    parent_notification_required = Faker("boolean", chance_of_getting_true=40)

    attendance_required_percentage = Faker(
        "random_element",
        elements=[
            Decimal("80.00"),
            Decimal("85.00"),
            Decimal("90.00"),
            Decimal("75.00"),
        ],
    )

    late_threshold_minutes = Faker("random_element", elements=[10, 15, 20, 30])

    default_code_window_minutes = Faker("random_element", elements=[10, 15, 20, 30])

    default_geofence_radius = Faker("random_element", elements=[25, 50, 75, 100])

    attendance_affects_grade = Faker("boolean", chance_of_getting_true=80)

    attendance_grade_weight = Faker(
        "random_element",
        elements=[
            Decimal("10.00"),
            Decimal("15.00"),
            Decimal("20.00"),
            Decimal("25.00"),
        ],
    )


class AttendanceSessionFactory(DjangoModelFactory):
    """Factory for creating attendance sessions."""

    class Meta:
        model = AttendanceSession

    attendance_settings = SubFactory(AttendanceSettingsFactory)

    session_date = Faker("date_between", start_date="-30d", end_date="today")

    start_time = Faker("time_object")

    end_time = factory.LazyAttribute(
        lambda obj: (datetime.combine(obj.session_date, obj.start_time) + timedelta(hours=1, minutes=30)).time(),
    )

    is_mandatory = Faker("boolean", chance_of_getting_true=85)

    is_substitute_session = Faker("boolean", chance_of_getting_true=10)

    substitute_reason = factory.LazyAttribute(
        lambda obj: (
            Faker(
                "random_element",
                elements=[
                    "Regular instructor illness",
                    "Conference attendance",
                    "Professional development",
                    "Emergency substitution",
                ],
            )
            if obj.is_substitute_session
            else ""
        ),
    )

    attendance_taken = Faker("boolean", chance_of_getting_true=90)

    attendance_taken_at = factory.LazyAttribute(
        lambda obj: (
            Faker(
                "date_time_between",
                start_date=obj.session_date,
                end_date=obj.session_date,
            )
            if obj.attendance_taken
            else None
        ),
    )

    notes = factory.LazyAttribute(
        lambda obj: (
            f"Substitute session: {obj.substitute_reason}"
            if obj.is_substitute_session
            else (Faker("sentence") if Faker("boolean", chance_of_getting_true=20) else "")
        ),
    )


class AttendanceRecordFactory(DjangoModelFactory):
    """Factory for creating attendance records."""

    class Meta:
        model = AttendanceRecord

    attendance_session = SubFactory(AttendanceSessionFactory)

    status = Faker(
        "random_element",
        elements=[
            "PRESENT",
            "PRESENT",
            "PRESENT",
            "PRESENT",  # Weight toward present
            "TARDY",
            "ABSENT",
            "EXCUSED",
        ],
    )

    check_in_time = factory.LazyAttribute(
        lambda obj: (
            (
                datetime.combine(
                    obj.attendance_session.session_date,
                    obj.attendance_session.start_time,
                )
                + timedelta(minutes=Faker('random_int', min=-5, max=20).generate({}))
            ).time()
            if obj.status in ["PRESENT", "TARDY"]
            else None
        ),
    )

    check_out_time = factory.LazyAttribute(
        lambda obj: (
            (
                datetime.combine(obj.attendance_session.session_date, obj.attendance_session.end_time)
                + timedelta(minutes=Faker('random_int', min=-10, max=5).generate({}))
            ).time()
            if obj.status == "PRESENT" and Faker("boolean", chance_of_getting_true=60)
            else None
        ),
    )

    excuse_reason = factory.LazyAttribute(
        lambda obj: (
            Faker(
                "random_element",
                elements=[
                    "Medical appointment",
                    "Family emergency",
                    "Religious observance",
                    "Transportation issue",
                    "Work conflict",
                    "Personal illness",
                ],
            )
            if obj.status in ["EXCUSED", "ABSENT"] and Faker("boolean", chance_of_getting_true=70)
            else ""
        ),
    )

    is_excused = factory.LazyAttribute(
        lambda obj: obj.status == "EXCUSED" or (obj.status == "ABSENT" and bool(obj.excuse_reason)),
    )

    minutes_late = factory.LazyAttribute(
        lambda obj: Faker("random_int", min=1, max=30) if obj.status == "TARDY" else 0,
    )

    notes = factory.LazyAttribute(
        lambda obj: (
            f"Late: {obj.minutes_late} minutes"
            if obj.status == "TARDY"
            else f"Excuse: {obj.excuse_reason}"
            if obj.excuse_reason
            else ""
        ),
    )


class PermissionRequestFactory(DjangoModelFactory):
    """Factory for creating permission requests."""

    class Meta:
        model = PermissionRequest

    request_type = Faker(
        "random_element",
        elements=["ABSENCE", "LATE_ARRIVAL", "EARLY_DEPARTURE", "MAKEUP_SESSION"],
    )

    request_date = Faker("date_between", start_date="-7d", end_date="+7d")

    reason = Faker(
        "random_element",
        elements=[
            "Medical appointment",
            "Family emergency",
            "Religious observance",
            "Academic conference",
            "Job interview",
            "Transportation delay",
            "Personal illness",
            "Family obligation",
        ],
    )

    detailed_explanation = factory.LazyAttribute(
        lambda obj: f"Request for {obj.request_type.lower().replace('_', ' ')} due to {obj.reason.lower()}. "
        f"This situation requires permission for {obj.request_date}.",
    )

    status = Faker(
        "random_element",
        elements=[
            "PENDING",
            "APPROVED",
            "DENIED",
            "APPROVED",
            "PENDING",  # Weight toward approved
        ],
    )

    reviewed_at = factory.LazyAttribute(
        lambda obj: (
            Faker("date_time_between", start_date=obj.request_date, end_date="now")
            if obj.status in ["APPROVED", "DENIED"]
            else None
        ),
    )

    reviewer_comments = factory.LazyAttribute(
        lambda obj: (
            Faker(
                "random_element",
                elements=[
                    "Approved - valid reason provided",
                    "Approved with documentation",
                    "Denied - insufficient justification",
                    "Approved - emergency situation",
                    "Please provide medical documentation",
                ],
            )
            if obj.status in ["APPROVED", "DENIED"] and Faker("boolean", chance_of_getting_true=60)
            else ""
        ),
    )


class RosterSyncFactory(DjangoModelFactory):
    """Factory for creating roster sync records."""

    class Meta:
        model = RosterSync

    sync_date = Faker("date_between", start_date="-7d", end_date="today")

    sync_type = Faker("random_element", elements=["MANUAL", "AUTOMATIC", "SCHEDULED", "EMERGENCY"])

    students_added = Faker("random_int", min=0, max=5)

    students_removed = Faker("random_int", min=0, max=2)

    sync_status = Faker(
        "random_element",
        elements=[
            "SUCCESS",
            "SUCCESS",
            "SUCCESS",
            "PARTIAL",
            "FAILED",  # Weight toward success
        ],
    )

    error_message = factory.LazyAttribute(
        lambda obj: (
            Faker(
                "random_element",
                elements=[
                    "Network timeout during sync",
                    "Student enrollment data mismatch",
                    "Permission denied for roster access",
                    "Invalid class session reference",
                ],
            )
            if obj.sync_status in ["FAILED", "PARTIAL"]
            else ""
        ),
    )

    sync_notes = factory.LazyAttribute(
        lambda obj: (
            f"Sync completed: +{obj.students_added} students, -{obj.students_removed} removed"
            if obj.sync_status == "SUCCESS"
            else (
                f"Partial sync: {obj.error_message}"
                if obj.sync_status == "PARTIAL"
                else f"Failed: {obj.error_message}"
            )
        ),
    )


class AttendanceArchiveFactory(DjangoModelFactory):
    """Factory for creating attendance archives."""

    class Meta:
        model = AttendanceArchive

    archive_date = Faker("date_between", start_date="-90d", end_date="-30d")

    archive_type = Faker("random_element", elements=["END_OF_TERM", "MANUAL", "AUTOMATIC", "CLEANUP"])

    records_archived = Faker("random_int", min=100, max=5000)

    archive_file_path = factory.LazyAttribute(
        lambda obj: f"/archives/attendance_{obj.archive_date.strftime('%Y_%m_%d')}_{obj.archive_type.lower()}.zip",
    )

    archive_size_mb = Faker("random_element", elements=["1.2", "5.7", "12.4", "8.9", "15.3", "22.1"])

    archive_status = Faker(
        "random_element",
        elements=["COMPLETED", "COMPLETED", "COMPLETED", "IN_PROGRESS", "FAILED"],
    )

    archive_notes = factory.LazyAttribute(
        lambda obj: (
            f"Archived {obj.records_archived} attendance records ({obj.archive_size_mb}MB)"
            if obj.archive_status == "COMPLETED"
            else (
                f"Archive in progress: {obj.records_archived} records"
                if obj.archive_status == "IN_PROGRESS"
                else "Archive failed - see logs for details"
            )
        ),
    )


# Utility factory for creating complete attendance scenarios
class AttendanceScenarioFactory:
    """Factory for creating complete attendance scenarios with related data."""

    @classmethod
    def create_class_attendance_for_week(cls, class_session, students, week_start_date):
        """Create a week's worth of attendance for a class."""
        attendance_records = []

        # Create attendance settings for the class
        settings = AttendanceSettingsFactory(
            name=f"Policy for {class_session}",
            grace_period_minutes=10,
            auto_mark_absent=True,
        )

        # Create attendance sessions for each day of the week
        for day_offset in range(5):  # Monday through Friday
            session_date = week_start_date + timedelta(days=day_offset)

            attendance_session = AttendanceSessionFactory(
                attendance_settings=settings,
                session_date=session_date,
                attendance_taken=True,
            )

            # Create attendance records for each student
            for _student in students:
                # Simulate realistic attendance patterns
                attendance_rate = Faker(
                    "random_element",
                    elements=[
                        0.95,  # Excellent attendance
                        0.85,  # Good attendance
                        0.75,  # Average attendance
                        0.60,  # Poor attendance
                    ],
                )

                is_present = Faker("boolean", chance_of_getting_true=int(attendance_rate * 100))

                if is_present:
                    status = Faker(
                        "random_element",
                        elements=["PRESENT", "PRESENT", "PRESENT", "TARDY"],
                    )
                else:
                    status = Faker("random_element", elements=["ABSENT", "EXCUSED"])

                record = AttendanceRecordFactory(
                    attendance_session=attendance_session,
                    status=status,
                )
                attendance_records.append(record)

        return attendance_records

    @classmethod
    def create_student_attendance_pattern(cls, student, term_sessions, attendance_pattern="good"):
        """Create consistent attendance pattern for a student across term sessions."""
        patterns = {
            "excellent": {
                "present_rate": 0.95,
                "tardy_rate": 0.03,
                "excused_rate": 0.02,
            },
            "good": {"present_rate": 0.85, "tardy_rate": 0.08, "excused_rate": 0.07},
            "average": {"present_rate": 0.75, "tardy_rate": 0.10, "excused_rate": 0.15},
            "poor": {"present_rate": 0.60, "tardy_rate": 0.15, "excused_rate": 0.25},
        }

        pattern_config = patterns.get(attendance_pattern, patterns["good"])
        records = []

        for session in term_sessions:
            rand_val = Faker("random_int", min=1, max=100) / 100

            if rand_val <= pattern_config["present_rate"]:
                status = "PRESENT"
            elif rand_val <= pattern_config["present_rate"] + pattern_config["tardy_rate"]:
                status = "TARDY"
            elif (
                rand_val
                <= pattern_config["present_rate"] + pattern_config["tardy_rate"] + pattern_config["excused_rate"]
            ):
                status = "EXCUSED"
            else:
                status = "ABSENT"

            record = AttendanceRecordFactory(
                attendance_session=session,
                status=status,
            )
            records.append(record)

        return records
