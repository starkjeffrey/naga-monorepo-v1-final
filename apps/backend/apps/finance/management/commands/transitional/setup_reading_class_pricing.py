"""
Setup reading class pricing records.

Creates ReadingClassPricing records for all cycles and tiers based on
historical patterns and current pricing models.
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.curriculum.models import Cycle
from apps.finance.models.pricing import ReadingClassPricing


class Command(BaseCommand):
    """Setup reading class pricing for all cycles and tiers."""

    help = "Create ReadingClassPricing records for all cycles and tiers"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("📚 Setting up Reading Class Pricing"))

        with transaction.atomic():
            created_count = self._create_reading_class_pricing()

        self.stdout.write(self.style.SUCCESS(f"✅ Created {created_count} reading class pricing records"))

    def _create_reading_class_pricing(self):
        """Create reading class pricing for all cycles and tiers."""

        self.stdout.write("\n💰 Creating ReadingClassPricing records...")

        # Define pricing structure
        # Based on the principle that smaller classes cost more per student
        # These are reasonable estimates based on typical reading class economics
        pricing_data = {
            # High School - lower base rates
            "HS": {
                "1-2": {"domestic": 200, "international": 250},  # Tutorial rate
                "3-5": {"domestic": 150, "international": 200},  # Small class
                "6-15": {"domestic": 100, "international": 150},  # Medium class
            },
            # Certificate programs
            "CERT": {
                "1-2": {"domestic": 250, "international": 300},
                "3-5": {"domestic": 200, "international": 250},
                "6-15": {"domestic": 150, "international": 200},
            },
            # Preparatory/Foundation
            "PREP": {
                "1-2": {"domestic": 250, "international": 300},
                "3-5": {"domestic": 200, "international": 250},
                "6-15": {"domestic": 150, "international": 200},
            },
            # Bachelor's degree - standard rates
            "BA": {
                "1-2": {"domestic": 300, "international": 350},  # Tutorial rate
                "3-5": {"domestic": 250, "international": 300},  # Small class
                "6-15": {"domestic": 200, "international": 250},  # Medium class
            },
            # Master's degree - higher rates
            "MA": {
                "1-2": {"domestic": 400, "international": 450},  # Tutorial rate
                "3-5": {"domestic": 350, "international": 400},  # Small class
                "6-15": {"domestic": 300, "international": 350},  # Medium class
            },
            # PhD - highest rates
            "PHD": {
                "1-2": {"domestic": 500, "international": 550},  # Tutorial rate
                "3-5": {"domestic": 450, "international": 500},  # Small class
                "6-15": {"domestic": 400, "international": 450},  # Medium class
            },
        }

        created_count = 0

        for cycle_code, tier_pricing in pricing_data.items():
            # Get or create the cycle
            try:
                cycle = Cycle.objects.get(code=cycle_code)
            except Cycle.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Cycle '{cycle_code}' not found, skipping"))
                continue

            for tier, prices in tier_pricing.items():
                # Check if pricing already exists for this cycle and tier
                exists = ReadingClassPricing.objects.filter(
                    cycle=cycle,
                    tier=tier,
                    end_date__isnull=True,  # Current pricing
                ).exists()

                if exists:
                    self.stdout.write(
                        self.style.WARNING(f"   ⚠️  Pricing for {cycle_code} {tier} already exists, skipping")
                    )
                    continue

                # Create the pricing record
                pricing = ReadingClassPricing.objects.create(
                    cycle=cycle,
                    tier=tier,
                    domestic_price=Decimal(str(prices["domestic"])),
                    international_price=Decimal(str(prices["international"])),
                    effective_date=date(2023, 1, 1),  # Effective from 2023
                    notes=f"Standard reading class pricing for {cycle.name} - {tier} students",
                )

                created_count += 1
                self.stdout.write(
                    f"   ✅ Created: {cycle_code} {tier} - "
                    f"${prices['domestic']} (domestic) / ${prices['international']} (international)"
                )

        # Display summary
        self.stdout.write("\n📊 READING CLASS PRICING SUMMARY:")

        for cycle in Cycle.objects.all().order_by("level"):
            self.stdout.write(f"\n   {cycle.name} ({cycle.code}):")

            pricing_records = ReadingClassPricing.objects.filter(cycle=cycle, end_date__isnull=True).order_by("tier")

            if not pricing_records.exists():
                self.stdout.write("      No pricing records")
                continue

            for pricing in pricing_records:
                self.stdout.write(f"      {pricing.tier}: ${pricing.domestic_price} / ${pricing.international_price}")

        # Check for special considerations
        self.stdout.write("\n📝 NOTES:")
        self.stdout.write("   • Tutorial rate (1-2 students) is highest per student")
        self.stdout.write("   • Price per student decreases as class size increases")
        self.stdout.write("   • International rates are typically 20-50% higher")
        self.stdout.write("   • These rates apply from 2023 onwards")
        self.stdout.write("   • Historical rates may need separate records with different effective dates")

        return created_count
