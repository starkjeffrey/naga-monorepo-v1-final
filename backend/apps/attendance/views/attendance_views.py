"""Real-time attendance tracking views with HTMX integration.

This module provides comprehensive attendance management functionality including:
- Real-time attendance marking interface
- Class roster management with quick actions
- Student search and bulk attendance operations
- Mobile-optimized teacher interfaces
- Attendance analytics and reporting

Key features:
- HTMX real-time updates without page refresh
- Barcode/QR code scanning support
- Bulk attendance marking with validation
- Comprehensive audit trails
- Mobile-first responsive design
"""

import json
import logging
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from apps.attendance.models import AttendanceRecord, AttendanceSession
from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader

logger = logging.getLogger(__name__)


class AttendanceDashboardView(LoginRequiredMixin, TemplateView):
    """Main attendance management dashboard with real-time updates."""

    template_name = "attendance/attendance_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current user's teaching assignments if they're a teacher
        user_teacher = None
        if hasattr(self.request.user, "teacher_profile"):
            user_teacher = self.request.user.teacher_profile

        # Get today's classes for this teacher
        today = timezone.now().date()
        current_classes = []

        if user_teacher:
            current_classes = (
                ClassHeader.objects.filter(
                    teacher=user_teacher, term__start_date__lte=today, term__end_date__gte=today, is_active=True
                )
                .select_related("course", "term")
                .prefetch_related("class_sessions", "enrollments__student__person")[:10]
            )
        else:
            # For admin users, show all active classes
            current_classes = ClassHeader.objects.filter(
                term__start_date__lte=today, term__end_date__gte=today, is_active=True
            ).select_related("course", "term", "teacher")[:20]

        # Calculate attendance statistics
        total_sessions_today = AttendanceSession.objects.filter(session_date=today).count()

        total_records_today = AttendanceRecord.objects.filter(attendance_session__session_date=today).count()

        attendance_rate_today = 0
        if total_records_today > 0:
            present_today = AttendanceRecord.objects.filter(
                attendance_session__session_date=today, attendance_status="present"
            ).count()
            attendance_rate_today = round((present_today / total_records_today) * 100, 1)

        # Recent attendance activity
        recent_sessions = (
            AttendanceSession.objects.filter(session_date__gte=today - timedelta(days=7))
            .select_related("class_header__course", "class_header__teacher", "recorded_by")
            .order_by("-session_date", "-start_time")[:10]
        )

        context.update(
            {
                "current_classes": current_classes,
                "user_teacher": user_teacher,
                "total_sessions_today": total_sessions_today,
                "total_records_today": total_records_today,
                "attendance_rate_today": attendance_rate_today,
                "recent_sessions": recent_sessions,
                "today": today,
            }
        )

        return context


@login_required
def class_attendance_view(request, class_header_id):
    """Main attendance interface for a specific class."""
    class_header = get_object_or_404(ClassHeader, id=class_header_id)

    # Check if user has permission to mark attendance for this class
    user_teacher = None
    if hasattr(request.user, "teacher_profile"):
        user_teacher = request.user.teacher_profile

    if user_teacher != class_header.teacher and not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Get or create today's attendance session
    today = timezone.now().date()
    current_time = timezone.now().time()

    attendance_session, created = AttendanceSession.objects.get_or_create(
        class_header=class_header,
        session_date=today,
        defaults={
            "start_time": current_time,
            "recorded_by": request.user,
            "session_notes": f"Session created by {request.user.get_full_name() or request.user.email}",
        },
    )

    # Get enrolled students with their attendance records
    enrolled_students = (
        ClassHeaderEnrollment.objects.filter(class_header=class_header, enrollment_status="enrolled")
        .select_related("student__person")
        .prefetch_related(
            Prefetch(
                "student__attendance_records",
                queryset=AttendanceRecord.objects.filter(attendance_session=attendance_session),
                to_attr="todays_attendance",
            )
        )
        .order_by("student__student_id")
    )

    # Prepare student data with attendance status
    student_data = []
    for enrollment in enrolled_students:
        student = enrollment.student
        attendance_record = None

        if student.todays_attendance:
            attendance_record = student.todays_attendance[0]

        student_data.append(
            {
                "enrollment": enrollment,
                "student": student,
                "attendance_record": attendance_record,
                "attendance_status": attendance_record.attendance_status if attendance_record else "not_marked",
                "check_in_time": attendance_record.check_in_time if attendance_record else None,
                "notes": attendance_record.notes if attendance_record else "",
            }
        )

    # Calculate attendance statistics
    total_students = len(student_data)
    present_count = sum(1 for s in student_data if s["attendance_status"] == "present")
    absent_count = sum(1 for s in student_data if s["attendance_status"] == "absent")
    late_count = sum(1 for s in student_data if s["attendance_status"] == "late")
    excused_count = sum(1 for s in student_data if s["attendance_status"] == "excused")
    not_marked_count = sum(1 for s in student_data if s["attendance_status"] == "not_marked")

    attendance_rate = round((present_count / total_students * 100), 1) if total_students > 0 else 0

    context = {
        "class_header": class_header,
        "attendance_session": attendance_session,
        "student_data": student_data,
        "total_students": total_students,
        "present_count": present_count,
        "absent_count": absent_count,
        "late_count": late_count,
        "excused_count": excused_count,
        "not_marked_count": not_marked_count,
        "attendance_rate": attendance_rate,
        "today": today,
        "session_created": created,
    }

    return render(request, "attendance/class_attendance.html", context)


@login_required
@require_http_methods(["POST"])
def mark_attendance(request, class_header_id):
    """HTMX endpoint for marking individual student attendance."""
    class_header = get_object_or_404(ClassHeader, id=class_header_id)

    # Permission check
    user_teacher = None
    if hasattr(request.user, "teacher_profile"):
        user_teacher = request.user.teacher_profile

    if user_teacher != class_header.teacher and not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    student_id = request.POST.get("student_id")
    attendance_status = request.POST.get("attendance_status")
    notes = request.POST.get("notes", "")

    if not student_id or not attendance_status:
        return JsonResponse({"error": "Missing required fields"}, status=400)

    # Validate attendance status
    valid_statuses = ["present", "absent", "late", "excused"]
    if attendance_status not in valid_statuses:
        return JsonResponse({"error": "Invalid attendance status"}, status=400)

    try:
        student = StudentProfile.objects.get(id=student_id)

        # Get today's attendance session
        today = timezone.now().date()
        attendance_session = AttendanceSession.objects.filter(class_header=class_header, session_date=today).first()

        if not attendance_session:
            return JsonResponse({"error": "No attendance session found for today"}, status=400)

        # Update or create attendance record
        attendance_record, _created = AttendanceRecord.objects.update_or_create(
            student=student,
            attendance_session=attendance_session,
            defaults={
                "attendance_status": attendance_status,
                "check_in_time": timezone.now().time() if attendance_status in ["present", "late"] else None,
                "notes": notes,
                "recorded_by": request.user,
                "recorded_at": timezone.now(),
            },
        )

        # Log the attendance change
        logger.info(f"Attendance marked: {student.student_id} - {attendance_status} by {request.user.email}")

        # Return updated student row
        context = {
            "student": student,
            "attendance_record": attendance_record,
            "attendance_status": attendance_status,
            "check_in_time": attendance_record.check_in_time,
            "notes": attendance_record.notes,
            "class_header": class_header,
        }

        return render(request, "attendance/partials/student_row.html", context)

    except StudentProfile.DoesNotExist:
        return JsonResponse({"error": "Student not found"}, status=404)
    except Exception as e:
        logger.error(f"Error marking attendance: {e}")
        return JsonResponse({"error": "Failed to mark attendance"}, status=500)


@login_required
def attendance_roster(request, class_header_id):
    """HTMX endpoint for refreshing attendance roster."""
    class_header = get_object_or_404(ClassHeader, id=class_header_id)

    # Get today's attendance session
    today = timezone.now().date()
    attendance_session = AttendanceSession.objects.filter(class_header=class_header, session_date=today).first()

    if not attendance_session:
        return JsonResponse({"error": "No attendance session found"}, status=400)

    # Get enrolled students with attendance records
    enrolled_students = (
        ClassHeaderEnrollment.objects.filter(class_header=class_header, enrollment_status="enrolled")
        .select_related("student__person")
        .prefetch_related(
            Prefetch(
                "student__attendance_records",
                queryset=AttendanceRecord.objects.filter(attendance_session=attendance_session),
                to_attr="todays_attendance",
            )
        )
        .order_by("student__student_id")
    )

    # Prepare student data
    student_data = []
    for enrollment in enrolled_students:
        student = enrollment.student
        attendance_record = None

        if student.todays_attendance:
            attendance_record = student.todays_attendance[0]

        student_data.append(
            {
                "student": student,
                "attendance_record": attendance_record,
                "attendance_status": attendance_record.attendance_status if attendance_record else "not_marked",
                "check_in_time": attendance_record.check_in_time if attendance_record else None,
                "notes": attendance_record.notes if attendance_record else "",
            }
        )

    context = {
        "student_data": student_data,
        "class_header": class_header,
        "attendance_session": attendance_session,
    }

    return render(request, "attendance/partials/attendance_roster.html", context)


@login_required
@require_http_methods(["POST"])
def quick_mark_all(request, class_header_id):
    """HTMX endpoint for bulk marking attendance (all present/absent)."""
    class_header = get_object_or_404(ClassHeader, id=class_header_id)

    # Permission check
    user_teacher = None
    if hasattr(request.user, "teacher_profile"):
        user_teacher = request.user.teacher_profile

    if user_teacher != class_header.teacher and not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    mark_as = request.POST.get("mark_as")  # 'present' or 'absent'

    if mark_as not in ["present", "absent"]:
        return JsonResponse({"error": "Invalid bulk marking option"}, status=400)

    try:
        # Get today's attendance session
        today = timezone.now().date()
        attendance_session = AttendanceSession.objects.filter(class_header=class_header, session_date=today).first()

        if not attendance_session:
            return JsonResponse({"error": "No attendance session found for today"}, status=400)

        # Get all enrolled students
        enrolled_students = ClassHeaderEnrollment.objects.filter(
            class_header=class_header, enrollment_status="enrolled"
        ).values_list("student", flat=True)

        # Bulk update attendance records
        updated_count = 0
        for student_id in enrolled_students:
            _attendance_record, _created = AttendanceRecord.objects.update_or_create(
                student_id=student_id,
                attendance_session=attendance_session,
                defaults={
                    "attendance_status": mark_as,
                    "check_in_time": timezone.now().time() if mark_as == "present" else None,
                    "recorded_by": request.user,
                    "recorded_at": timezone.now(),
                },
            )
            updated_count += 1

        logger.info(f"Bulk attendance marked: {updated_count} students marked as {mark_as} by {request.user.email}")

        return JsonResponse(
            {
                "success": True,
                "message": f"Marked {updated_count} students as {mark_as}",
                "updated_count": updated_count,
            }
        )

    except Exception as e:
        logger.error(f"Error in bulk attendance marking: {e}")
        return JsonResponse({"error": "Failed to mark attendance"}, status=500)


@login_required
def attendance_report(request, class_header_id):
    """Generate attendance report for a class."""
    class_header = get_object_or_404(ClassHeader, id=class_header_id)

    # Permission check
    user_teacher = None
    if hasattr(request.user, "teacher_profile"):
        user_teacher = request.user.teacher_profile

    if user_teacher != class_header.teacher and not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Get date range (default to current term)
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if not start_date:
        start_date = class_header.term.start_date
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Get attendance sessions in date range
    attendance_sessions = AttendanceSession.objects.filter(
        class_header=class_header, session_date__gte=start_date, session_date__lte=end_date
    ).order_by("session_date")

    # Get enrolled students
    enrolled_students = (
        ClassHeaderEnrollment.objects.filter(class_header=class_header, enrollment_status="enrolled")
        .select_related("student__person")
        .order_by("student__student_id")
    )

    # Calculate attendance statistics per student
    student_stats = []
    for enrollment in enrolled_students:
        student = enrollment.student

        # Get attendance records for this student in the date range
        records = AttendanceRecord.objects.filter(student=student, attendance_session__in=attendance_sessions)

        total_sessions = attendance_sessions.count()
        total_records = records.count()
        present_count = records.filter(attendance_status="present").count()
        absent_count = records.filter(attendance_status="absent").count()
        late_count = records.filter(attendance_status="late").count()
        excused_count = records.filter(attendance_status="excused").count()

        attendance_rate = round((present_count / total_sessions * 100), 1) if total_sessions > 0 else 0

        student_stats.append(
            {
                "student": student,
                "total_sessions": total_sessions,
                "total_records": total_records,
                "present_count": present_count,
                "absent_count": absent_count,
                "late_count": late_count,
                "excused_count": excused_count,
                "attendance_rate": attendance_rate,
            }
        )

    context = {
        "class_header": class_header,
        "start_date": start_date,
        "end_date": end_date,
        "attendance_sessions": attendance_sessions,
        "student_stats": student_stats,
        "total_sessions": attendance_sessions.count(),
    }

    return render(request, "attendance/attendance_report.html", context)


@login_required
def student_attendance_search(request):
    """HTMX endpoint for searching students by ID or name."""
    query = request.GET.get("q", "").strip()
    class_header_id = request.GET.get("class_header_id")

    if not query or len(query) < 2:
        return JsonResponse({"students": []})

    # Search students
    students = StudentProfile.objects.filter(
        Q(student_id__icontains=query) | Q(person__name_en__icontains=query) | Q(person__name_km__icontains=query)
    ).select_related("person")[:10]

    # If class_header_id provided, check enrollment status
    if class_header_id:
        try:
            class_header = ClassHeader.objects.get(id=class_header_id)
            enrolled_student_ids = ClassHeaderEnrollment.objects.filter(
                class_header=class_header, enrollment_status="enrolled"
            ).values_list("student_id", flat=True)

            students = students.filter(id__in=enrolled_student_ids)
        except ClassHeader.DoesNotExist:
            pass

    student_data = []
    for student in students:
        student_data.append(
            {
                "id": student.id,
                "student_id": student.student_id,
                "name_en": student.person.name_en,
                "name_km": student.person.name_km or "",
            }
        )

    return JsonResponse({"students": student_data})


@login_required
@require_http_methods(["POST"])
def bulk_attendance_update(request):
    """HTMX endpoint for updating multiple attendance records."""
    attendance_data = request.POST.get("attendance_data")
    class_header_id = request.POST.get("class_header_id")

    if not attendance_data or not class_header_id:
        return JsonResponse({"error": "Missing required data"}, status=400)

    try:
        class_header = get_object_or_404(ClassHeader, id=class_header_id)

        # Permission check
        user_teacher = None
        if hasattr(request.user, "teacher_profile"):
            user_teacher = request.user.teacher_profile

        if user_teacher != class_header.teacher and not request.user.is_staff:
            return JsonResponse({"error": "Permission denied"}, status=403)

        # Parse attendance data (JSON format expected)
        attendance_updates = json.loads(attendance_data)

        # Get today's attendance session
        today = timezone.now().date()
        attendance_session = AttendanceSession.objects.filter(class_header=class_header, session_date=today).first()

        if not attendance_session:
            return JsonResponse({"error": "No attendance session found for today"}, status=400)

        updated_count = 0
        errors = []

        for update in attendance_updates:
            try:
                student_id = update.get("student_id")
                attendance_status = update.get("status")
                notes = update.get("notes", "")

                if not student_id or not attendance_status:
                    continue

                student = StudentProfile.objects.get(id=student_id)

                _attendance_record, _created = AttendanceRecord.objects.update_or_create(
                    student=student,
                    attendance_session=attendance_session,
                    defaults={
                        "attendance_status": attendance_status,
                        "check_in_time": timezone.now().time() if attendance_status in ["present", "late"] else None,
                        "notes": notes,
                        "recorded_by": request.user,
                        "recorded_at": timezone.now(),
                    },
                )

                updated_count += 1

            except StudentProfile.DoesNotExist:
                errors.append(f"Student {student_id} not found")
            except Exception as e:
                errors.append(f"Error updating student {student_id}: {e!s}")

        logger.info(f"Bulk attendance update: {updated_count} records updated by {request.user.email}")

        response_data = {
            "success": True,
            "updated_count": updated_count,
            "message": f"Updated {updated_count} attendance records",
        }

        if errors:
            response_data["errors"] = errors

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid attendance data format"}, status=400)
    except Exception as e:
        logger.error(f"Error in bulk attendance update: {e}")
        return JsonResponse({"error": "Failed to update attendance records"}, status=500)
