#!/usr/bin/env python
"""Debug the promotion system step by step."""

import os
import sys

import django

sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.curriculum.models import Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.language.services import LanguagePromotionService
from apps.scheduling.models import ClassHeader


def debug_promotion():
    # Get existing data
    source_term = Term.objects.get(name="ENG A 2024-1")
    target_term = Term.objects.get(name="ENG A 2024-2")

    # Check existing classes
    source_classes = ClassHeader.objects.filter(term=source_term)
    target_classes = ClassHeader.objects.filter(term=target_term)

    for _cls in source_classes:
        pass

    for _cls in target_classes:
        pass

    # Check enrollments
    enrollments = ClassHeaderEnrollment.objects.filter(
        class_header__term=source_term,
        class_header__course__code__startswith="EHSS",
    ).select_related("student__person", "class_header__course")

    for _enrollment in enrollments[:5]:  # Show first 5
        pass

    # Test class cloning specifically
    source_class = source_classes.filter(course__code="EHSS-05").first()
    if source_class:
        try:
            cloned_class = LanguagePromotionService._clone_class_for_next_level(source_class, target_term, "EHSS")
            if cloned_class:
                pass
            else:
                pass
        except Exception:
            pass
    else:
        pass


if __name__ == "__main__":
    debug_promotion()
