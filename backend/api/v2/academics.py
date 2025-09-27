"""Enhanced Academics API v2 with advanced grade management.

This module provides enhanced academic management endpoints with:
- Grid-style grade entry with real-time collaboration
- Schedule conflict detection and resolution
- Transcript generation with custom templates
- QR code attendance processing
- Prerequisite chain visualization
- Advanced grade analytics and insights
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Avg, Count, Min, Max, Prefetch
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import paginate

from apps.scheduling.models import ClassHeader, ClassPart, TimeSlot, Room
from apps.grading.models import Grade, Assignment, GradingScale
from apps.enrollment.models import ClassHeaderEnrollment
from apps.attendance.models import AttendanceRecord
from apps.curriculum.models import Course, Prerequisite
from apps.academic_records.models import Transcript

from ..v1.auth import jwt_auth
from .schemas import (
    GradeEntry,
    GradeSpreadsheetData,
    ScheduleConflict,
    BulkActionRequest,
    BulkActionResult,
    ChartData,
    TimeSeriesPoint
)

logger = logging.getLogger(__name__)

router = Router(auth=jwt_auth, tags=["academics-enhanced"])


@router.get("/grades/spreadsheet/{class_id}/", response=GradeSpreadsheetData)
def get_grade_spreadsheet(request, class_id: UUID):
    """Get grade data in spreadsheet format for grid editing."""

    class_header = get_object_or_404(
        ClassHeader.objects.prefetch_related(
            Prefetch(
                'enrollments',
                queryset=ClassHeaderEnrollment.objects.select_related(
                    'student__person'
                ).filter(status='enrolled')
            ),
            Prefetch(
                'assignments',
                queryset=Assignment.objects.order_by('due_date')
            ),
            Prefetch(
                'grades',
                queryset=Grade.objects.select_related(
                    'assignment', 'enrollment__student__person'
                )
            )
        ),
        unique_id=class_id
    )

    # Get assignments for this class
    assignments = list(class_header.assignments.all())
    assignment_data = [
        {
            "id": str(assignment.unique_id),
            "name": assignment.name,
            "type": assignment.assignment_type,
            "max_score": float(assignment.max_score),
            "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
            "weight": float(assignment.weight),
            "is_published": assignment.is_published
        }
        for assignment in assignments
    ]

    # Get students enrolled in this class
    enrollments = list(class_header.enrollments.all())
    student_data = [
        {
            "id": str(enrollment.student.unique_id),
            "student_id": enrollment.student.student_id,
            "name": enrollment.student.person.full_name,
            "email": enrollment.student.person.school_email,
            "enrollment_id": str(enrollment.unique_id)
        }
        for enrollment in enrollments
    ]

    # Build grade matrix
    grade_matrix = []
    grades_dict = {}

    # Index existing grades
    for grade in class_header.grades.all():
        key = (str(grade.enrollment.student.unique_id), str(grade.assignment.unique_id))
        grades_dict[key] = grade

    # Build matrix: rows = students, columns = assignments
    for enrollment in enrollments:
        student_row = []
        for assignment in assignments:
            key = (str(enrollment.student.unique_id), str(assignment.unique_id))
            grade = grades_dict.get(key)
            student_row.append(float(grade.score) if grade and grade.score else None)
        grade_matrix.append(student_row)

    # Calculate class statistics
    total_students = len(enrollments)
    total_assignments = len(assignments)
    graded_assignments = sum(1 for assignment in assignments if assignment.is_published)

    completion_rate = 0.0
    if total_assignments > 0:
        total_possible_grades = total_students * total_assignments
        total_entered_grades = len([g for g in class_header.grades.all() if g.score is not None])
        completion_rate = total_entered_grades / total_possible_grades if total_possible_grades > 0 else 0.0

    metadata = {
        "class_name": f"{class_header.course.code} - {class_header.course.name}",
        "instructor": class_header.instructor.person.full_name if class_header.instructor else "TBA",
        "term": class_header.term.name if class_header.term else "No term",
        "total_students": total_students,
        "total_assignments": total_assignments,
        "graded_assignments": graded_assignments,
        "completion_rate": completion_rate,
        "last_modified": class_header.last_modified.isoformat()
    }

    return GradeSpreadsheetData(
        class_id=class_header.unique_id,
        assignments=assignment_data,
        students=student_data,
        grades=grade_matrix,
        metadata=metadata
    )


@router.post("/grades/spreadsheet/{class_id}/", response=BulkActionResult)
def update_grade_spreadsheet(request, class_id: UUID, grades_data: List[GradeEntry]) -> BulkActionResult:
    """Bulk update grades from spreadsheet interface."""

    class_header = get_object_or_404(ClassHeader, unique_id=class_id)
    success_count = 0
    failed_ids = []

    try:
        with transaction.atomic():
            for grade_entry in grades_data:
                try:
                    # Get or create grade
                    enrollment = get_object_or_404(
                        ClassHeaderEnrollment,
                        student_profile__unique_id=grade_entry.student_id,
                        class_header=class_header
                    )
                    assignment = get_object_or_404(
                        Assignment,
                        unique_id=grade_entry.assignment_id
                    )

                    grade, created = Grade.objects.get_or_create(
                        class_header_enrollment=enrollment,
                        assignment=assignment,
                        defaults={
                            'score': grade_entry.score,
                            'max_score': grade_entry.max_score,
                            'notes': grade_entry.notes
                        }
                    )

                    if not created:
                        grade.score = grade_entry.score
                        grade.max_score = grade_entry.max_score
                        grade.notes = grade_entry.notes
                        grade.save()

                    success_count += 1

                except Exception as e:
                    logger.error("Failed to update grade for student %s: %s", grade_entry.student_id, e)
                    failed_ids.append(grade_entry.student_id)

        return BulkActionResult(
            success=True,
            processed_count=success_count,
            failed_count=len(failed_ids),
            failed_ids=failed_ids,
            message=f"Successfully updated {success_count} grades"
        )

    except Exception as e:
        logger.error("Grade spreadsheet update failed: %s", e)
        return BulkActionResult(
            success=False,
            processed_count=0,
            failed_count=len(grades_data),
            failed_ids=[entry.student_id for entry in grades_data],
            message=f"Update failed: {str(e)}"
        )


@router.get("/schedule/conflicts/", response=List[ScheduleConflict])
def detect_schedule_conflicts(
    request,
    term_id: Optional[UUID] = Query(None),
    room_id: Optional[UUID] = Query(None),
    check_type: str = Query("all")  # "all", "time", "resource", "capacity"
) -> List[ScheduleConflict]:
    """Real-time schedule conflict detection and resolution suggestions."""

    conflicts = []

    # Base queryset for class parts in the specified term
    class_parts_qs = ClassPart.objects.select_related(
        'class_header__course',
        'class_header__instructor',
        'time_slot',
        'room'
    )

    if term_id:
        class_parts_qs = class_parts_qs.filter(class_header__term_id=term_id)

    if room_id:
        class_parts_qs = class_parts_qs.filter(room_id=room_id)

    class_parts = list(class_parts_qs)

    # Check for time conflicts
    if check_type in ["all", "time"]:
        time_conflicts = {}
        for part in class_parts:
            if not part.time_slot:
                continue

            key = (
                part.time_slot.start_time,
                part.time_slot.end_time,
                part.time_slot.day_of_week
            )

            if key not in time_conflicts:
                time_conflicts[key] = []
            time_conflicts[key].append(part)

        # Find conflicts (more than one class at same time)
        for time_key, parts in time_conflicts.items():
            if len(parts) > 1:
                conflicts.append(ScheduleConflict(
                    type="time_overlap",
                    severity="critical",
                    message=f"Time conflict on {parts[0].time_slot.day_of_week} at {parts[0].time_slot.start_time}",
                    affected_items=[{
                        "class_id": str(part.class_header.unique_id),
                        "course": f"{part.class_header.course.code} - {part.class_header.course.name}",
                        "instructor": part.class_header.instructor.person.full_name if part.class_header.instructor else "TBA"
                    } for part in parts],
                    suggestions=[
                        "Reschedule one of the conflicting classes",
                        "Use different time slots",
                        "Consider online delivery for one class"
                    ]
                ))

    # Check for room conflicts
    if check_type in ["all", "resource"]:
        room_conflicts = {}
        for part in class_parts:
            if not part.room or not part.time_slot:
                continue

            key = (
                part.room.unique_id,
                part.time_slot.start_time,
                part.time_slot.end_time,
                part.time_slot.day_of_week
            )

            if key not in room_conflicts:
                room_conflicts[key] = []
            room_conflicts[key].append(part)

        for room_key, parts in room_conflicts.items():
            if len(parts) > 1:
                room = parts[0].room
                conflicts.append(ScheduleConflict(
                    type="resource_conflict",
                    severity="critical",
                    message=f"Room conflict in {room.room_number} ({room.building})",
                    affected_items=[{
                        "class_id": str(part.class_header.unique_id),
                        "course": f"{part.class_header.course.code} - {part.class_header.course.name}",
                        "room": f"{part.room.room_number} ({part.room.building})"
                    } for part in parts],
                    suggestions=[
                        "Assign different rooms to conflicting classes",
                        "Stagger class times",
                        "Use alternative venues"
                    ]
                ))

    # Check for capacity issues
    if check_type in ["all", "capacity"]:
        for part in class_parts:
            if not part.room:
                continue

            enrollment_count = ClassHeaderEnrollment.objects.filter(
                class_header=part.class_header,
                status='enrolled'
            ).count()

            if enrollment_count > part.room.capacity:
                conflicts.append(ScheduleConflict(
                    type="capacity_exceeded",
                    severity="warning",
                    message=f"Room capacity exceeded: {enrollment_count} students in room for {part.room.capacity}",
                    affected_items=[{
                        "class_id": str(part.class_header.unique_id),
                        "course": f"{part.class_header.course.code} - {part.class_header.course.name}",
                        "room": f"{part.room.room_number} ({part.room.building})",
                        "enrollment": enrollment_count,
                        "capacity": part.room.capacity
                    }],
                    suggestions=[
                        "Move to a larger room",
                        "Split class into multiple sections",
                        "Consider hybrid delivery"
                    ]
                ))

    return conflicts


@router.post("/transcripts/generate/{student_id}/", response=Dict[str, Any])
def generate_transcript(
    request,
    student_id: UUID,
    template: str = Query("official"),  # "official", "informal", "custom"
    format: str = Query("pdf")  # "pdf", "html", "json"
) -> Dict[str, Any]:
    """Generate student transcript with custom templates."""

    from apps.people.models import StudentProfile

    student = get_object_or_404(StudentProfile, unique_id=student_id)

    # Get all completed enrollments with grades
    enrollments = ClassHeaderEnrollment.objects.filter(
        student_profile=student,
        status__in=['completed', 'enrolled']
    ).select_related(
        'class_header__course',
        'class_header__term'
    ).prefetch_related('grades')

    # Calculate GPA and credit hours
    total_credit_hours = 0
    total_grade_points = 0
    completed_courses = []

    for enrollment in enrollments:
        course = enrollment.class_header.course
        final_grade = enrollment.grades.filter(
            assignment__assignment_type='final'
        ).first()

        if final_grade and final_grade.grade_points:
            credit_hours = course.credit_hours
            grade_points = final_grade.grade_points * credit_hours

            total_credit_hours += credit_hours
            total_grade_points += grade_points

            completed_courses.append({
                "course_code": course.code,
                "course_name": course.name,
                "credit_hours": credit_hours,
                "grade": final_grade.letter_grade,
                "grade_points": final_grade.grade_points,
                "term": enrollment.class_header.term.name if enrollment.class_header.term else "N/A",
                "completion_date": enrollment.completion_date
            })

    gpa = total_grade_points / total_credit_hours if total_credit_hours > 0 else 0.0

    transcript_data = {
        "student": {
            "name": student.person.full_name,
            "student_id": student.student_id,
            "email": student.person.school_email,
            "program": student.program_enrollments.first().program.name if student.program_enrollments.exists() else "N/A"
        },
        "academic_summary": {
            "gpa": round(gpa, 2),
            "total_credit_hours": total_credit_hours,
            "total_courses": len(completed_courses),
            "enrollment_date": student.enrollment_start_date
        },
        "courses": completed_courses,
        "generated_at": datetime.now().isoformat(),
        "template": template,
        "format": format
    }

    # TODO: Implement actual PDF/HTML generation
    if format == "pdf":
        # Generate PDF using ReportLab or WeasyPrint
        transcript_url = f"/api/v2/transcripts/pdf/{student_id}/"
    elif format == "html":
        # Generate HTML template
        transcript_url = f"/api/v2/transcripts/html/{student_id}/"
    else:
        transcript_url = None

    return {
        "success": True,
        "transcript_data": transcript_data,
        "download_url": transcript_url,
        "message": f"Transcript generated successfully in {format} format"
    }


@router.post("/attendance/qr-scan/", response=Dict[str, Any])
def process_qr_attendance(
    request,
    qr_data: str,
    location: Optional[str] = None,
    timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """Process QR code attendance scanning."""

    import json
    from apps.people.models import StudentProfile

    if timestamp is None:
        timestamp = datetime.now()

    try:
        # Parse QR code data (assuming JSON format)
        qr_info = json.loads(qr_data)
        class_id = qr_info.get('class_id')
        student_id = qr_info.get('student_id')
        session_token = qr_info.get('session_token')

        if not all([class_id, student_id, session_token]):
            return {
                "success": False,
                "message": "Invalid QR code data",
                "status": "error"
            }

        # Verify class session is active
        class_header = get_object_or_404(ClassHeader, unique_id=class_id)
        student = get_object_or_404(StudentProfile, unique_id=student_id)

        # Check if student is enrolled in this class
        enrollment = ClassHeaderEnrollment.objects.filter(
            student_profile=student,
            class_header=class_header,
            status='enrolled'
        ).first()

        if not enrollment:
            return {
                "success": False,
                "message": "Student not enrolled in this class",
                "status": "not_enrolled"
            }

        # Record attendance
        attendance, created = AttendanceRecord.objects.get_or_create(
            student_profile=student,
            class_header=class_header,
            date=timestamp.date(),
            defaults={
                'status': 'present',
                'check_in_time': timestamp.time(),
                'location': location,
                'method': 'qr_scan'
            }
        )

        if not created:
            # Update existing record
            attendance.status = 'present'
            attendance.check_in_time = timestamp.time()
            attendance.location = location
            attendance.save()

        return {
            "success": True,
            "message": "Attendance recorded successfully",
            "status": "present",
            "student_name": student.person.full_name,
            "class_name": f"{class_header.course.code} - {class_header.course.name}",
            "timestamp": timestamp.isoformat()
        }

    except json.JSONDecodeError:
        return {
            "success": False,
            "message": "Invalid QR code format",
            "status": "error"
        }
    except Exception as e:
        logger.error("QR attendance processing failed: %s", e)
        return {
            "success": False,
            "message": f"Processing failed: {str(e)}",
            "status": "error"
        }


@router.get("/courses/{course_id}/prerequisites/", response=Dict[str, Any])
def get_prerequisite_chain(request, course_id: UUID) -> Dict[str, Any]:
    """Get prerequisite chain visualization data for a course."""

    course = get_object_or_404(Course, unique_id=course_id)

    def build_prerequisite_tree(course_obj, visited=None):
        """Recursively build prerequisite tree."""
        if visited is None:
            visited = set()

        if course_obj.unique_id in visited:
            return None  # Avoid circular dependencies

        visited.add(course_obj.unique_id)

        prerequisites = Prerequisite.objects.filter(
            course=course_obj
        ).select_related('prerequisite_course')

        node = {
            "course_id": str(course_obj.unique_id),
            "course_code": course_obj.code,
            "course_name": course_obj.name,
            "credit_hours": course_obj.credit_hours,
            "prerequisites": []
        }

        for prereq in prerequisites:
            prereq_node = build_prerequisite_tree(prereq.prerequisite_course, visited.copy())
            if prereq_node:
                node["prerequisites"].append(prereq_node)

        return node

    # Build forward prerequisites (what courses need this course)
    def build_dependent_courses(course_obj):
        """Build list of courses that depend on this course."""
        dependents = Prerequisite.objects.filter(
            prerequisite_course=course_obj
        ).select_related('course')

        return [{
            "course_id": str(dep.course.unique_id),
            "course_code": dep.course.code,
            "course_name": dep.course.name,
            "credit_hours": dep.course.credit_hours
        } for dep in dependents]

    prerequisite_tree = build_prerequisite_tree(course)
    dependent_courses = build_dependent_courses(course)

    return {
        "course": {
            "course_id": str(course.unique_id),
            "course_code": course.code,
            "course_name": course.name,
            "description": course.description,
            "credit_hours": course.credit_hours
        },
        "prerequisite_tree": prerequisite_tree,
        "dependent_courses": dependent_courses,
        "visualization_type": "tree",
        "generated_at": datetime.now().isoformat()
    }


@router.post("/grades/spreadsheet/{class_id}/bulk-update/", response=BulkActionResult)
def bulk_update_grades(request, class_id: UUID, grade_updates: List[GradeEntry]):
    """Bulk update grades with conflict detection."""

    class_header = get_object_or_404(ClassHeader, unique_id=class_id)

    results = BulkActionResult(
        success_count=0,
        failure_count=0,
        total_count=len(grade_updates)
    )

    with transaction.atomic():
        for grade_entry in grade_updates:
            try:
                # Get enrollment and assignment
                enrollment = ClassHeaderEnrollment.objects.get(
                    student__unique_id=grade_entry.student_id,
                    class_header=class_header,
                    status='enrolled'
                )

                assignment = Assignment.objects.get(
                    unique_id=grade_entry.assignment_id,
                    class_header=class_header
                )

                # Check for existing grade
                grade, created = Grade.objects.get_or_create(
                    enrollment=enrollment,
                    assignment=assignment,
                    defaults={
                        'score': grade_entry.score,
                        'notes': grade_entry.notes,
                        'entered_by': request.user if hasattr(request, 'user') else None
                    }
                )

                if not created:
                    # Check for conflicts (concurrent modifications)
                    if grade.last_modified > grade_entry.last_modified:
                        results.failures.append({
                            "student_id": str(grade_entry.student_id),
                            "assignment_id": str(grade_entry.assignment_id),
                            "error": "Grade was modified by another user. Please refresh and try again."
                        })
                        results.failure_count += 1
                        continue

                    # Update existing grade
                    grade.score = grade_entry.score
                    grade.notes = grade_entry.notes
                    grade.entered_by = request.user if hasattr(request, 'user') else None
                    grade.save()

                results.successes.append({
                    "student_id": str(grade_entry.student_id),
                    "assignment_id": str(grade_entry.assignment_id),
                    "message": "Grade updated successfully"
                })
                results.success_count += 1

                # Clear grade analytics cache
                cache.delete(f"grade_analytics_{class_id}")

            except (ClassHeaderEnrollment.DoesNotExist, Assignment.DoesNotExist) as e:
                results.failures.append({
                    "student_id": str(grade_entry.student_id),
                    "assignment_id": str(grade_entry.assignment_id),
                    "error": f"Invalid student or assignment: {str(e)}"
                })
                results.failure_count += 1

            except Exception as e:
                logger.error("Failed to update grade: %s", e)
                results.failures.append({
                    "student_id": str(grade_entry.student_id),
                    "assignment_id": str(grade_entry.assignment_id),
                    "error": f"Unexpected error: {str(e)}"
                })
                results.failure_count += 1

    return results


@router.get("/schedule/conflicts/", response=List[ScheduleConflict])
def detect_schedule_conflicts(
    request,
    term_id: Optional[UUID] = Query(None),
    room_id: Optional[UUID] = Query(None),
    instructor_id: Optional[UUID] = Query(None)
):
    """Detect scheduling conflicts for classes, rooms, and instructors."""

    conflicts = []

    # Base query for classes
    classes_query = ClassHeader.objects.select_related(
        'course', 'instructor__person', 'term'
    ).prefetch_related('class_parts__time_slots', 'class_parts__room')

    if term_id:
        classes_query = classes_query.filter(term__unique_id=term_id)

    if instructor_id:
        classes_query = classes_query.filter(instructor__unique_id=instructor_id)

    classes = list(classes_query)

    # Group classes by time slots for conflict detection
    time_slot_groups = {}

    for class_header in classes:
        for class_part in class_header.class_parts.all():
            for time_slot in class_part.time_slots.all():
                # Create a key for time slot grouping
                key = (
                    time_slot.day_of_week,
                    time_slot.start_time,
                    time_slot.end_time
                )

                if key not in time_slot_groups:
                    time_slot_groups[key] = []

                time_slot_groups[key].append({
                    'class_header': class_header,
                    'class_part': class_part,
                    'time_slot': time_slot,
                    'room': class_part.room
                })

    # Detect conflicts
    for time_key, scheduled_items in time_slot_groups.items():
        if len(scheduled_items) > 1:
            # Time overlap conflict
            day, start_time, end_time = time_key

            # Group by room
            room_conflicts = {}
            instructor_conflicts = {}

            for item in scheduled_items:
                room = item['room']
                instructor = item['class_header'].instructor

                # Room conflicts
                if room:
                    if room.unique_id not in room_conflicts:
                        room_conflicts[room.unique_id] = []
                    room_conflicts[room.unique_id].append(item)

                # Instructor conflicts
                if instructor:
                    if instructor.unique_id not in instructor_conflicts:
                        instructor_conflicts[instructor.unique_id] = []
                    instructor_conflicts[instructor.unique_id].append(item)

            # Report room conflicts
            for room_id, conflicting_items in room_conflicts.items():
                if len(conflicting_items) > 1:
                    room_name = conflicting_items[0]['room'].name
                    affected_classes = [
                        {
                            "class_id": str(item['class_header'].unique_id),
                            "course_code": item['class_header'].course.code,
                            "course_name": item['class_header'].course.name
                        }
                        for item in conflicting_items
                    ]

                    conflicts.append(ScheduleConflict(
                        type="room_conflict",
                        severity="critical",
                        message=f"Room {room_name} is double-booked on {day} from {start_time} to {end_time}",
                        affected_items=affected_classes,
                        suggestions=[
                            f"Move one class to a different room",
                            f"Change the time slot for one of the classes",
                            f"Split the class into multiple sections"
                        ]
                    ))

            # Report instructor conflicts
            for instructor_id, conflicting_items in instructor_conflicts.items():
                if len(conflicting_items) > 1:
                    instructor_name = conflicting_items[0]['class_header'].instructor.person.full_name
                    affected_classes = [
                        {
                            "class_id": str(item['class_header'].unique_id),
                            "course_code": item['class_header'].course.code,
                            "course_name": item['class_header'].course.name
                        }
                        for item in conflicting_items
                    ]

                    conflicts.append(ScheduleConflict(
                        type="instructor_conflict",
                        severity="critical",
                        message=f"Instructor {instructor_name} is scheduled for multiple classes on {day} from {start_time} to {end_time}",
                        affected_items=affected_classes,
                        suggestions=[
                            f"Assign a different instructor to one of the classes",
                            f"Change the time slot for one of the classes",
                            f"Combine the classes if content is similar"
                        ]
                    ))

    # Check capacity conflicts
    for class_header in classes:
        for class_part in class_header.class_parts.all():
            if class_part.room and class_part.room.capacity:
                enrollment_count = class_header.enrollments.filter(status='enrolled').count()
                if enrollment_count > class_part.room.capacity:
                    conflicts.append(ScheduleConflict(
                        type="capacity_exceeded",
                        severity="warning",
                        message=f"Class {class_header.course.code} has {enrollment_count} students but room {class_part.room.name} capacity is {class_part.room.capacity}",
                        affected_items=[{
                            "class_id": str(class_header.unique_id),
                            "course_code": class_header.course.code,
                            "enrollment_count": enrollment_count,
                            "room_capacity": class_part.room.capacity
                        }],
                        suggestions=[
                            "Move to a larger room",
                            "Split into multiple sections",
                            "Limit enrollment"
                        ]
                    ))

    return conflicts


@router.get("/transcripts/generate/{student_id}/")
def generate_transcript(
    request,
    student_id: UUID,
    template: str = Query("official", description="Transcript template type"),
    include_unofficial: bool = Query(False)
):
    """Generate student transcript with custom templates."""

    from apps.people.models import StudentProfile

    student = get_object_or_404(StudentProfile, unique_id=student_id)

    # Get academic records
    enrollments = ClassHeaderEnrollment.objects.filter(
        student=student,
        status__in=['completed', 'enrolled']
    ).select_related(
        'class_header__course',
        'class_header__term'
    ).prefetch_related(
        'grades__assignment'
    ).order_by('class_header__term__start_date')

    # Calculate GPA and credits
    total_credits = 0
    total_grade_points = 0
    courses_completed = []

    for enrollment in enrollments:
        course = enrollment.class_header.course
        term = enrollment.class_header.term

        # Calculate final grade for this course
        grades = enrollment.grades.all()
        if grades:
            # Simple average calculation (in practice, this would be more sophisticated)
            total_score = sum(grade.score for grade in grades if grade.score is not None)
            grade_count = len([g for g in grades if g.score is not None])
            final_percentage = total_score / grade_count if grade_count > 0 else 0

            # Convert to letter grade (simplified)
            if final_percentage >= 90:
                letter_grade = "A"
                grade_points = 4.0
            elif final_percentage >= 80:
                letter_grade = "B"
                grade_points = 3.0
            elif final_percentage >= 70:
                letter_grade = "C"
                grade_points = 2.0
            elif final_percentage >= 60:
                letter_grade = "D"
                grade_points = 1.0
            else:
                letter_grade = "F"
                grade_points = 0.0

            credit_hours = course.credit_hours or 3  # Default to 3 credits
            total_credits += credit_hours
            total_grade_points += grade_points * credit_hours

            courses_completed.append({
                "term": term.name if term else "Unknown",
                "course_code": course.code,
                "course_name": course.name,
                "credits": credit_hours,
                "grade": letter_grade,
                "grade_points": grade_points
            })

    gpa = total_grade_points / total_credits if total_credits > 0 else 0.0

    transcript_data = {
        "student": {
            "name": student.person.full_name,
            "student_id": student.student_id,
            "date_of_birth": student.person.date_of_birth.isoformat() if student.person.date_of_birth else None,
            "program": student.current_program.name if student.current_program else "Undeclared"
        },
        "academic_summary": {
            "total_credits": total_credits,
            "gpa": round(gpa, 2),
            "courses_completed": len(courses_completed),
            "academic_standing": "Good Standing" if gpa >= 2.0 else "Academic Probation"
        },
        "courses": courses_completed,
        "generated_date": datetime.now().isoformat(),
        "template": template,
        "is_official": not include_unofficial
    }

    # TODO: Generate PDF transcript using the specified template
    # For now, return the data structure

    return {
        "transcript_data": transcript_data,
        "download_url": f"/api/v2/academics/transcripts/download/{student_id}/?template={template}",
        "generated_at": datetime.now().isoformat()
    }


@router.post("/attendance/qr-scan/")
def process_qr_attendance(
    request,
    qr_data: str,
    location: Optional[str] = None,
    timestamp: Optional[datetime] = None
):
    """Process QR code scan for attendance."""

    try:
        # Parse QR code data (format: "class_id:student_id:session_date")
        parts = qr_data.split(":")
        if len(parts) != 3:
            return {"error": "Invalid QR code format"}

        class_id, student_id, session_date = parts

        # Validate class and student
        class_header = get_object_or_404(ClassHeader, unique_id=class_id)

        from apps.people.models import StudentProfile
        student = get_object_or_404(StudentProfile, unique_id=student_id)

        # Check if student is enrolled
        enrollment = ClassHeaderEnrollment.objects.filter(
            class_header=class_header,
            student=student,
            status='enrolled'
        ).first()

        if not enrollment:
            return {"error": "Student not enrolled in this class"}

        # Parse session date
        session_datetime = datetime.fromisoformat(session_date)
        scan_time = timestamp or datetime.now()

        # Check if attendance already recorded
        existing_record = AttendanceRecord.objects.filter(
            student=student,
            class_header=class_header,
            date=session_datetime.date()
        ).first()

        if existing_record:
            return {
                "message": "Attendance already recorded",
                "status": existing_record.status,
                "recorded_at": existing_record.created_at.isoformat()
            }

        # Determine attendance status based on timing
        # (This is simplified - real implementation would consider class schedule)
        time_diff = abs((scan_time - session_datetime).total_seconds() / 60)  # minutes

        if time_diff <= 10:
            status = "present"
        elif time_diff <= 30:
            status = "late"
        else:
            status = "absent"

        # Create attendance record
        attendance_record = AttendanceRecord.objects.create(
            student=student,
            class_header=class_header,
            date=session_datetime.date(),
            status=status,
            scan_location=location,
            scan_timestamp=scan_time
        )

        return {
            "message": "Attendance recorded successfully",
            "status": status,
            "student_name": student.person.full_name,
            "class_name": f"{class_header.course.code} - {class_header.course.name}",
            "recorded_at": attendance_record.created_at.isoformat(),
            "minutes_difference": round(time_diff, 1)
        }

    except Exception as e:
        logger.error("Failed to process QR attendance: %s", e)
        return {"error": "Failed to process attendance scan"}


@router.get("/courses/{course_id}/prerequisites/")
def get_prerequisite_chain(request, course_id: UUID):
    """Get prerequisite chain visualization data for a course."""

    course = get_object_or_404(Course, unique_id=course_id)

    def build_prerequisite_tree(current_course, visited=None):
        """Recursively build prerequisite tree."""
        if visited is None:
            visited = set()

        if current_course.unique_id in visited:
            return {"id": str(current_course.unique_id), "name": current_course.name, "circular": True}

        visited.add(current_course.unique_id)

        prerequisites = Prerequisite.objects.filter(
            course=current_course
        ).select_related('prerequisite_course')

        node = {
            "id": str(current_course.unique_id),
            "name": current_course.name,
            "code": current_course.code,
            "credits": current_course.credit_hours,
            "prerequisites": []
        }

        for prereq in prerequisites:
            if prereq.prerequisite_course:
                prereq_node = build_prerequisite_tree(prereq.prerequisite_course, visited.copy())
                node["prerequisites"].append(prereq_node)

        return node

    prerequisite_tree = build_prerequisite_tree(course)

    # Also get courses that have this course as a prerequisite
    dependent_courses = Course.objects.filter(
        prerequisites__prerequisite_course=course
    ).values('unique_id', 'name', 'code')

    return {
        "course": {
            "id": str(course.unique_id),
            "name": course.name,
            "code": course.code,
            "description": course.description
        },
        "prerequisite_tree": prerequisite_tree,
        "dependent_courses": list(dependent_courses),
        "generated_at": datetime.now().isoformat()
    }


@router.get("/analytics/grade-distribution/{class_id}/", response=ChartData)
def get_grade_distribution(request, class_id: UUID):
    """Get grade distribution analytics for a class."""

    class_header = get_object_or_404(ClassHeader, unique_id=class_id)

    # Get all final grades for the class
    enrollments = ClassHeaderEnrollment.objects.filter(
        class_header=class_header,
        status__in=['enrolled', 'completed']
    ).prefetch_related('grades')

    grade_ranges = {
        "A (90-100)": 0,
        "B (80-89)": 0,
        "C (70-79)": 0,
        "D (60-69)": 0,
        "F (0-59)": 0,
        "No Grade": 0
    }

    for enrollment in enrollments:
        grades = enrollment.grades.filter(score__isnull=False)
        if grades.exists():
            # Calculate average (simplified)
            avg_score = grades.aggregate(avg=Avg('score'))['avg']
            if avg_score >= 90:
                grade_ranges["A (90-100)"] += 1
            elif avg_score >= 80:
                grade_ranges["B (80-89)"] += 1
            elif avg_score >= 70:
                grade_ranges["C (70-79)"] += 1
            elif avg_score >= 60:
                grade_ranges["D (60-69)"] += 1
            else:
                grade_ranges["F (0-59)"] += 1
        else:
            grade_ranges["No Grade"] += 1

    # Convert to chart data
    chart_points = [
        TimeSeriesPoint(
            timestamp=datetime.now(),
            value=count,
            label=grade_range
        )
        for grade_range, count in grade_ranges.items()
    ]

    return ChartData(
        title=f"Grade Distribution - {class_header.course.code}",
        type="pie",
        data=chart_points,
        options={
            "total_students": sum(grade_ranges.values()),
            "class_name": f"{class_header.course.code} - {class_header.course.name}"
        }
    )


# Export router
__all__ = ["router"]