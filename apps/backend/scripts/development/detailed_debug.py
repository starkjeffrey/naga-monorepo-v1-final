#!/usr/bin/env python
"""Detailed debug of the cloning function."""

import os
import sys

import django

sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.curriculum.models import Course, Term
from apps.language.services import LanguagePromotionService
from apps.scheduling.models import ClassHeader


def detailed_debug():
    # Get data
    source_term = Term.objects.get(name="ENG A 2024-1")
    target_term = Term.objects.get(name="ENG A 2024-2")
    source_class = ClassHeader.objects.get(term=source_term, course__code="EHSS-05", section_id="A")

    # Step by step through the cloning logic

    # Extract level
    current_level = LanguagePromotionService._extract_level_from_course_code(source_class.course.code)

    if current_level is None:
        return None

    # Calculate next level code
    next_level_code = f"EHSS-{(current_level + 1):02d}"

    # Check if next course exists
    try:
        next_course = Course.objects.get(code=next_level_code)
    except Course.DoesNotExist:
        return None

    # Try to create/get class
    try:
        cloned_class, _created = ClassHeader.objects.get_or_create(
            course=next_course,
            term=target_term,
            section_id=source_class.section_id,
            defaults={
                "max_enrollment": source_class.max_enrollment,
                "notes": f"Auto-cloned from {source_class.course.code} for level progression",
            },
        )

        # Check class sessions and parts
        class_sessions = source_class.class_sessions.all()
        sum(session.class_parts.count() for session in class_sessions)

        return cloned_class

    except Exception:
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = detailed_debug()
