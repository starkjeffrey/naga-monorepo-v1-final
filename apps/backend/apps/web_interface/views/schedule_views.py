"""Schedule builder and management views for the web interface."""

from __future__ import annotations

import json
from datetime import datetime, time
from typing import Any

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from apps.common.models import Room
from apps.curriculum.models import Course, Term
from apps.people.models import TeacherProfile
from apps.scheduling.models import ClassHeader, ClassPart, ClassSession


class ScheduleBuilderView(LoginRequiredMixin, TemplateView):
    """Visual schedule builder interface with drag-and-drop functionality."""

    template_name = "web_interface/pages/academic/schedule_builder.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add schedule builder context data."""
        context = super().get_context_data(**kwargs)

        # Get current term or allow term selection
        current_term = Term.objects.filter(is_active=True).first()
        all_terms = Term.objects.all().order_by("-term_id")

        # Get available resources
        courses = Course.objects.filter(is_active=True).order_by("course_code")
        rooms = Room.objects.filter(is_active=True).order_by("room_code")
        teachers = (
            TeacherProfile.objects.filter(person__user__is_active=True)
            .select_related("person")
            .order_by("person__last_name", "person__first_name")
        )

        context.update(
            {
                "current_term": current_term,
                "all_terms": all_terms,
                "courses": courses,
                "rooms": rooms,
                "teachers": teachers,
                "time_slots": self.get_time_slots(),
                "weekdays": self.get_weekdays(),
                "page_title": _("Schedule Builder"),
            }
        )

        return context

    def get_time_slots(self) -> list[dict[str, Any]]:
        """Get available time slots for scheduling."""
        time_slots = []

        # Generate time slots from 7:00 AM to 10:00 PM in 30-minute intervals
        start_hour = 7
        end_hour = 22

        for hour in range(start_hour, end_hour + 1):
            for minute in [0, 30]:
                if hour == end_hour and minute == 30:
                    break

                slot_time = time(hour, minute)
                time_slots.append(
                    {
                        "time": slot_time,
                        "display": slot_time.strftime("%I:%M %p"),
                        "value": slot_time.strftime("%H:%M"),
                    }
                )

        return time_slots

    def get_weekdays(self) -> list[dict[str, Any]]:
        """Get weekday options for scheduling."""
        return [
            {"value": "monday", "display": _("Monday"), "short": _("Mon")},
            {"value": "tuesday", "display": _("Tuesday"), "short": _("Tue")},
            {"value": "wednesday", "display": _("Wednesday"), "short": _("Wed")},
            {"value": "thursday", "display": _("Thursday"), "short": _("Thu")},
            {"value": "friday", "display": _("Friday"), "short": _("Fri")},
            {"value": "saturday", "display": _("Saturday"), "short": _("Sat")},
            {"value": "sunday", "display": _("Sunday"), "short": _("Sun")},
        ]


@login_required
@require_http_methods(["GET"])
def schedule_data(request: HttpRequest, term_id: int) -> JsonResponse:
    """HTMX endpoint to load schedule data for a specific term."""
    term = get_object_or_404(Term, id=term_id)

    # Get all class headers for this term
    class_headers = (
        ClassHeader.objects.filter(
            term=term,
            is_active=True,
        )
        .select_related("course", "term")
        .prefetch_related("classsession_set__classpart_set")
    )

    # Build schedule data structure
    schedule_data = []

    for class_header in class_headers:
        for session in class_header.classsession_set.filter(is_active=True):
            for part in session.classpart_set.all():
                # Get meeting days and times
                meeting_days = part.meeting_days or []

                if part.start_time and part.end_time and meeting_days:
                    schedule_item = {
                        "id": f"class_{class_header.id}_session_{session.id}_part_{part.id}",
                        "class_header_id": class_header.id,
                        "session_id": session.id,
                        "part_id": part.id,
                        "title": f"{class_header.course.course_code} - {part.part_name}",
                        "course_name": class_header.course.course_name,
                        "instructor": part.teacher.person.full_name if part.teacher else "",
                        "room": part.room.room_code if part.room else "",
                        "start_time": part.start_time.strftime("%H:%M"),
                        "end_time": part.end_time.strftime("%H:%M"),
                        "meeting_days": meeting_days,
                        "max_enrollment": class_header.max_enrollment,
                        "current_enrollment": getattr(class_header, "get_current_enrollment_count", lambda: 0)(),
                        "status": "active" if getattr(class_header, "is_active", False) else "inactive",
                    }
                    schedule_data.append(schedule_item)

    return JsonResponse(
        {
            "success": True,
            "schedule_data": schedule_data,
            "term": {
                "id": getattr(term, "pk", None),
                "name": str(term),
                "start_date": term.start_date.isoformat() if term.start_date else None,
                "end_date": term.end_date.isoformat() if term.end_date else None,
            },
        }
    )


@login_required
@require_http_methods(["POST"])
def create_class_schedule(request: HttpRequest) -> JsonResponse:
    """HTMX endpoint to create a new class schedule."""
    try:
        data = json.loads(request.body)

        # Required fields
        course_id = data.get("course_id")
        term_id = data.get("term_id")
        schedule_items = data.get("schedule_items", [])

        if not course_id or not term_id or not schedule_items:
            return JsonResponse({"success": False, "error": _("Missing required data")}, status=400)

        course = get_object_or_404(Course, id=course_id)
        term = get_object_or_404(Term, id=term_id)

        with transaction.atomic():
            # Create class header
            class_header = ClassHeader.objects.create(
                course=course,
                term=term,
                class_code=data.get("class_code", ""),
                max_enrollment=data.get("max_enrollment", 25),
                description=data.get("description", ""),
                is_active=True,
                created_by=request.user,
            )

            # Create sessions and parts based on schedule items
            session_number = 1
            for item in schedule_items:
                # Create session if it doesn't exist
                session, _created = ClassSession.objects.get_or_create(
                    class_header=class_header,
                    session_number=session_number,
                    defaults={
                        "session_name": item.get("session_name", f"Session {session_number}"),
                        "is_active": True,
                    },
                )

                # Create class part
                teacher = None
                if item.get("teacher_id"):
                    teacher = TeacherProfile.objects.get(id=item["teacher_id"])

                room = None
                if item.get("room_id"):
                    room = Room.objects.get(id=item["room_id"])

                ClassPart.objects.create(
                    class_session=session,
                    part_name=item.get("part_name", "Main"),
                    teacher=teacher,
                    room=room,
                    start_time=datetime.strptime(item["start_time"], "%H:%M").time(),
                    end_time=datetime.strptime(item["end_time"], "%H:%M").time(),
                    meeting_days=item.get("meeting_days", []),
                    credit_hours=item.get("credit_hours", getattr(course, "credit_hours", 0)),
                )

                session_number += 1

        return JsonResponse(
            {
                "success": True,
                "message": _("Class schedule created successfully"),
                "class_header_id": class_header.id,
            }
        )

    except ValidationError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception:
        return JsonResponse(
            {"success": False, "error": _("An error occurred while creating the schedule")}, status=500
        )


@login_required
@require_http_methods(["POST"])
def update_class_schedule(request: HttpRequest, class_header_id: int) -> JsonResponse:
    """HTMX endpoint to update an existing class schedule."""
    try:
        class_header = get_object_or_404(ClassHeader, id=class_header_id)
        data = json.loads(request.body)

        operation = data.get("operation")

        if operation == "move":
            # Move a class part to different time/room
            part_id = data.get("part_id")
            new_start_time = data.get("start_time")
            new_end_time = data.get("end_time")
            new_room_id = data.get("room_id")
            new_meeting_days = data.get("meeting_days")

            part = get_object_or_404(ClassPart, id=part_id, class_session__class_header=class_header)

            with transaction.atomic():
                if new_start_time:
                    part.start_time = datetime.strptime(new_start_time, "%H:%M").time()
                if new_end_time:
                    part.end_time = datetime.strptime(new_end_time, "%H:%M").time()
                if new_room_id:
                    part.room = Room.objects.get(id=new_room_id)
                if new_meeting_days:
                    part.meeting_days = new_meeting_days

                part.full_clean()
                part.save()

            return JsonResponse({"success": True, "message": _("Schedule updated successfully")})

        elif operation == "assign_teacher":
            # Assign teacher to class part
            part_id = data.get("part_id")
            teacher_id = data.get("teacher_id")

            part = get_object_or_404(ClassPart, id=part_id, class_session__class_header=class_header)
            teacher = get_object_or_404(TeacherProfile, id=teacher_id) if teacher_id else None

            part.teacher = teacher
            part.save()

            return JsonResponse({"success": True, "message": _("Teacher assigned successfully")})

        else:
            return JsonResponse({"success": False, "error": _("Invalid operation")}, status=400)

    except ValidationError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception:
        return JsonResponse(
            {"success": False, "error": _("An error occurred while updating the schedule")}, status=500
        )


@login_required
@require_http_methods(["POST"])
def check_schedule_conflicts(request: HttpRequest) -> JsonResponse:
    """HTMX endpoint to check for scheduling conflicts."""
    try:
        data = json.loads(request.body)

        teacher_id = data.get("teacher_id")
        room_id = data.get("room_id")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        meeting_days = data.get("meeting_days", [])
        term_id = data.get("term_id")
        exclude_part_id = data.get("exclude_part_id")  # For updates

        conflicts: list[dict[str, str]] = []

        if not start_time or not end_time or not meeting_days or not term_id:
            return JsonResponse({"success": True, "conflicts": conflicts})

        # Convert times
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        end_time_obj = datetime.strptime(end_time, "%H:%M").time()

        # Check for conflicts with existing class parts
        existing_parts = ClassPart.objects.filter(
            class_session__class_header__term_id=term_id,
            class_session__is_active=True,
        ).select_related("class_session__class_header__course", "teacher__person", "room")

        if exclude_part_id:
            existing_parts = existing_parts.exclude(id=exclude_part_id)

        for part in existing_parts:
            if not part.start_time or not part.end_time or not part.meeting_days:
                continue

            # Check time overlap
            time_overlap = start_time_obj < part.end_time and end_time_obj > part.start_time

            # Check day overlap
            day_overlap = bool(set(meeting_days) & set(part.meeting_days))

            if time_overlap and day_overlap:
                # Check specific conflicts
                conflict_type = None
                conflict_details = None

                if teacher_id and part.teacher_id == int(teacher_id):
                    conflict_type = "teacher"
                    conflict_details = f"Teacher {part.teacher.person.full_name}"
                elif room_id and part.room_id == int(room_id):
                    conflict_type = "room"
                    conflict_details = f"Room {part.room.room_code}"

                if conflict_type:
                    conflicts.append(
                        {
                            "type": conflict_type,
                            "details": conflict_details,
                            "class": f"{part.class_session.class_header.course.course_code}",
                            "time": f"{part.start_time.strftime('%H:%M')} - {part.end_time.strftime('%H:%M')}",
                            "days": part.meeting_days,
                        }
                    )

        return JsonResponse({"success": True, "conflicts": conflicts})

    except Exception:
        return JsonResponse({"success": False, "error": _("An error occurred while checking conflicts")}, status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_class_schedule(request: HttpRequest, class_header_id: int) -> JsonResponse:
    """HTMX endpoint to delete a class schedule."""
    try:
        class_header = get_object_or_404(ClassHeader, id=class_header_id)

        # Check if class has enrollments
        if class_header.get_current_enrollment_count() > 0:
            return JsonResponse(
                {"success": False, "error": _("Cannot delete class with active enrollments")}, status=400
            )

        with transaction.atomic():
            # Soft delete by setting is_active to False
            class_header.is_active = False
            class_header.save()

            # Also deactivate sessions
            class_header.classsession_set.update(is_active=False)

        return JsonResponse({"success": True, "message": _("Class schedule deleted successfully")})

    except Exception:
        return JsonResponse(
            {"success": False, "error": _("An error occurred while deleting the schedule")}, status=500
        )
