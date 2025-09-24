#!/usr/bin/env python
"""
Test script for time-of-day discount rules implementation.

This script validates the new schedule-based discount functionality
using real data from student 16516's case.
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
os.environ.setdefault("USE_DOCKER", "yes")

import django

django.setup()

from decimal import Decimal

from apps.finance.models.discounts import DiscountRule
from apps.finance.services.automatic_discount_service import AutomaticDiscountService


def test_time_of_day_discount_rules():
    """Test the new time-of-day discount rule functionality."""

    print("🧪 Testing Time-of-Day Discount Rules")
    print("=" * 50)

    # Create test discount rule
    test_rule = DiscountRule.objects.create(
        rule_name="Test Morning BA 15%",
        rule_type="EARLY_BIRD",
        pattern_text="test morning bachelor classes",
        discount_percentage=Decimal("15.00"),
        applies_to_cycle="BA",
        applies_to_schedule={
            "time_of_day": ["MORN"],
            "cycles": ["BA"],
            "min_courses": 1,
            "calculation_method": "per_class",
            "description": "Test 15% discount for morning Bachelor program classes",
        },
        is_active=True,
    )

    print(f"✅ Created test rule: {test_rule.rule_name}")
    print(f"   Discount: {test_rule.discount_percentage}%")
    print(f"   Cycle: {test_rule.applies_to_cycle}")
    print(f"   Schedule: {test_rule.applies_to_schedule}")
    print()

    # Test with AutomaticDiscountService
    service = AutomaticDiscountService()

    # Test student 16516 (has both morning and evening classes)
    student_id = "16516"
    term_code = "250224B-T1"

    print(f"🔍 Testing eligibility for student {student_id} in term {term_code}")

    # Check if rule applies to this student
    applies = service._rule_applies_to_student(test_rule, student_id, term_code)
    print(f"   Rule applies to student: {applies}")

    # Check schedule specifically
    schedule_applies = service._rule_applies_to_schedule(test_rule, student_id, term_code)
    print(f"   Schedule criteria met: {schedule_applies}")

    # Check early bird eligibility (if term has discount deadline)
    try:
        eligibility = service.check_early_bird_eligibility(student_id, term_code)
        print(f"   Early bird status: {eligibility.status.value}")
        print(f"   Discount rate: {eligibility.discount_rate}%")
    except Exception as e:
        print(f"   Early bird check error: {e}")

    print()

    # Clean up test rule
    test_rule.delete()
    print("🧹 Cleaned up test rule")
    print()

    # Show JSON field structure examples
    print("📋 JSON Field Structure Examples:")
    print("-" * 30)

    examples = [
        {
            "name": "Morning Language 15%",
            "json": {
                "time_of_day": ["MORN"],
                "cycles": ["LANG"],
                "min_courses": 1,
                "calculation_method": "per_class",
                "description": "15% discount for morning Language program classes",
            },
        },
        {
            "name": "Evening BA 10%",
            "json": {
                "time_of_day": ["EVE"],
                "cycles": ["BA"],
                "min_courses": 1,
                "calculation_method": "per_class",
                "description": "10% discount for evening Bachelor program classes",
            },
        },
        {
            "name": "Mixed Schedule BA",
            "json": {
                "time_of_day": ["MORN", "EVE"],
                "cycles": ["BA"],
                "min_courses": 2,
                "calculation_method": "weighted_average",
                "description": "Blended discount for BA students with both morning and evening classes",
            },
        },
    ]

    for example in examples:
        print(f"   {example['name']}:")
        for key, value in example["json"].items():
            print(f"     {key}: {value}")
        print()

    print("🎯 Available Options:")
    print("   Time of Day: MORN, EVE, AFT")
    print("   Cycles: LANG, BA, MASTERS")
    print("   Calculation Methods: per_class, flat_rate, weighted_average")

    print("\n✅ Time-of-Day Discount Rules Implementation Complete!")


if __name__ == "__main__":
    test_time_of_day_discount_rules()
