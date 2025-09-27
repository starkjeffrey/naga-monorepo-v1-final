#!/usr/bin/env python
"""
Examples of the updated Fee Pricing system.

Shows how to use the new DOCUMENT fee type and is_per_document field
to create flexible pricing for different types of fees.
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
from typing import Any

from apps.finance.models.pricing import FeeType


def show_fee_pricing_examples():
    """Show examples of the updated fee pricing system."""

    print("📋 Fee Pricing System Examples")
    print("=" * 50)

    # Example fees with different frequency types
    examples: list[dict[str, Any]] = [
        {
            "name": "Registration Fee",
            "fee_type": FeeType.REGISTRATION,
            "local_amount": Decimal("50.00"),
            "foreign_amount": Decimal("75.00"),
            "is_mandatory": True,
            "is_per_term": True,
            "description": "One-time registration fee charged once per term regardless of course count",
        },
        {
            "name": "Material Fee",
            "fee_type": FeeType.MATERIAL,
            "local_amount": Decimal("10.00"),
            "foreign_amount": Decimal("15.00"),
            "is_mandatory": True,
            "is_per_course": True,
            "description": "Material fee charged for each course enrollment",
        },
        {
            "name": "Official Transcript",
            "fee_type": FeeType.DOCUMENT,
            "local_amount": Decimal("5.00"),
            "foreign_amount": Decimal("10.00"),
            "is_mandatory": False,
            "is_per_document": True,
            "description": "Fee for each official transcript requested",
        },
        {
            "name": "Degree Certificate",
            "fee_type": FeeType.DOCUMENT,
            "local_amount": Decimal("25.00"),
            "foreign_amount": Decimal("35.00"),
            "is_mandatory": False,
            "is_per_document": True,
            "description": "Fee for each degree certificate copy requested",
        },
        {
            "name": "Course Completion Certificate",
            "fee_type": FeeType.DOCUMENT,
            "local_amount": Decimal("10.00"),
            "foreign_amount": Decimal("15.00"),
            "is_mandatory": False,
            "is_per_document": True,
            "description": "Fee for each course completion certificate requested",
        },
    ]

    print("💰 Fee Examples:")
    print("-" * 20)

    for example in examples:
        frequency = ""
        if example.get("is_per_term"):
            frequency = "Per Term"
        elif example.get("is_per_course"):
            frequency = "Per Course"
        elif example.get("is_per_document"):
            frequency = "Per Document"
        else:
            frequency = "One-time"

        mandatory = "Mandatory" if example["is_mandatory"] else "Optional"

        print(f"📄 {example['name']}")
        print(f"   Type: {example['fee_type'].replace('_', ' ').title()}")
        print(f"   Pricing: ${example['local_amount']} local / ${example['foreign_amount']} foreign")
        print(f"   Frequency: {frequency}")
        print(f"   Status: {mandatory}")
        print(f"   Description: {example['description']}")
        print()

    print("🎯 Key Changes Made:")
    print("-" * 20)
    print("✅ Changed 'TRANSCRIPT' fee type to 'DOCUMENT' (broader scope)")
    print("✅ Added 'is_per_document' field for document-based pricing")
    print("✅ Improved help text for all frequency fields:")
    print("   • is_per_course: Charged once for EACH course enrollment")
    print("   • is_per_term: Charged once per term regardless of course count")
    print("   • is_per_document: Charged for each document requested")
    print("   • is_mandatory: If true = auto-charged, if false = on-request")
    print()

    print("📊 Pricing Scenarios:")
    print("-" * 20)
    print("Student taking 3 courses in a term:")
    print("• Registration Fee (per term): $50 x 1 = $50")
    print("• Material Fee (per course): $10 x 3 = $30")
    print("• If they request 2 transcripts: $5 x 2 = $10")
    print("• Total: $90")
    print()

    print("Foreign student taking 2 courses:")
    print("• Registration Fee (per term): $75 x 1 = $75")
    print("• Material Fee (per course): $15 x 2 = $30")
    print("• If they request 1 degree certificate: $35 x 1 = $35")
    print("• Total: $140")
    print()

    print("✅ Fee Pricing System Updated Successfully!")


if __name__ == "__main__":
    show_fee_pricing_examples()
