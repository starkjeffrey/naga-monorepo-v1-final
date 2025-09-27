"""
Setup discount rules based on historical analysis.

This command:
1. Updates Term table to set discount_end_date for Rule 4 (7 days after start_date)
2. Creates DiscountRule records for the 4 historical periods
"""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.curriculum.models import Term
from apps.finance.models import DiscountRule


class Command(BaseCommand):
    """Setup discount rules and term discount dates."""

    help = "Setup discount rules based on historical analysis"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("📊 Setting up discount rules"))

        with transaction.atomic():
            # Step 1: Update Term discount_end_date for Rule 4 (2023 onwards)
            self._update_term_discount_dates()

            # Step 2: Create DiscountRule records
            self._create_discount_rules()

        self.stdout.write(self.style.SUCCESS("✅ Discount rules setup complete"))

    def _update_term_discount_dates(self):
        """Update discount_end_date for terms from 2023 onwards (7 days after start)."""

        self.stdout.write("\n📅 Updating Term discount_end_date for 2023+ terms...")

        # Get terms that should have 7-day early bird
        # Term codes starting with 23, 24, 25 (2023 onwards)
        terms_to_update = Term.objects.filter(code__regex=r"^(23|24|25)").exclude(start_date__isnull=True)

        updated_count = 0
        for term in terms_to_update:
            if term.start_date:
                # Set discount_end_date to 7 days after start_date
                term.discount_end_date = term.start_date + timedelta(days=7)
                term.save(update_fields=["discount_end_date"])
                updated_count += 1

                self.stdout.write(f"   Updated {term.code}: {term.start_date} → {term.discount_end_date}")

        self.stdout.write(self.style.SUCCESS(f"   ✅ Updated {updated_count} terms with 7-day discount windows"))

    def _create_discount_rules(self):
        """Create the 4 historical discount rules."""

        self.stdout.write("\n💰 Creating DiscountRule records...")

        # Define the 4 rules
        rules = [
            {
                "rule_name": "Historical 15% Discount (2018-2019)",
                "rule_type": "EARLY_BIRD",
                "discount_percentage": Decimal("15.00"),
                "pattern_text": "15% early bird discount",
                "applies_to_terms": ["2018T1", "2018T2E", "2018T3E", "2018T4E", "2019T1E", "2019T4E"],
                "is_active": False,  # Historical only
            },
            {
                "rule_name": "COVID Peak 20% Discount",
                "rule_type": "EARLY_BIRD",
                "discount_percentage": Decimal("20.00"),
                "pattern_text": "20% COVID discount",
                "applies_to_terms": ["2019-2020T1", "2019-2020T3", "2020T1E", "2020T1IFL"],
                "is_active": False,
            },
            {
                "rule_name": "COVID Standard 15% Discount",
                "rule_type": "EARLY_BIRD",
                "discount_percentage": Decimal("15.00"),
                "pattern_text": "15% COVID discount",
                "applies_to_terms": [],  # Too many terms - will set separately
                "is_active": False,
            },
            {
                "rule_name": "Modern 10% Early Bird",
                "rule_type": "EARLY_BIRD",
                "discount_percentage": Decimal("10.00"),
                "pattern_text": "10% early bird discount",
                "applies_to_terms": [],  # Applies to all 2023+ terms
                "is_active": True,  # Currently active
            },
        ]

        created_count = 0
        for rule_data in rules:
            # Check if rule already exists
            exists = DiscountRule.objects.filter(rule_name=rule_data["rule_name"]).exists()

            if exists:
                self.stdout.write(
                    self.style.WARNING(f"   ⚠️  Rule '{rule_data['rule_name']}' already exists, skipping")
                )
                continue

            # Create the rule
            rule = DiscountRule.objects.create(
                rule_name=rule_data["rule_name"],
                rule_type=rule_data["rule_type"],
                discount_percentage=rule_data["discount_percentage"],
                pattern_text=rule_data["pattern_text"],
                applies_to_terms=rule_data["applies_to_terms"],
                is_active=rule_data["is_active"],
                # Set applies_to_cycle as empty to apply to all cycles
                applies_to_cycle="",
                # No programs restriction
                applies_to_programs=[],
            )

            # Special handling for COVID Standard and Modern rules
            if rule.rule_name == "COVID Standard 15% Discount":
                # Set the many terms for COVID period
                covid_terms = [
                    "2019-2020T2E",
                    "2020-2021T1",
                    "2020-2021T4E",
                    "2021-2021T1",
                    "2021T2T2",
                    "2021T3",
                    "2021T3E",
                    "2021T4E",
                    "2021-2022T1",
                    "2022AT3E",
                    "2022T1T1E",
                    "2022T2",
                    "2022T2T2",
                    "2022T3E",
                    "2022T4ET4E",
                ]
                rule.applies_to_terms = covid_terms
                rule.save()

            created_count += 1
            terms_info = f"{len(rule.applies_to_terms)} terms" if rule.applies_to_terms else "All matching terms"
            self.stdout.write(f"   ✅ Created: {rule.rule_name} ({rule.discount_percentage}%) [{terms_info}]")

        self.stdout.write(self.style.SUCCESS(f"\n   ✅ Created {created_count} discount rules"))

        # Display summary
        self.stdout.write("\n📊 DISCOUNT RULES SUMMARY:")
        all_rules = DiscountRule.objects.filter(rule_type="EARLY_BIRD").order_by("created_at")

        for rule in all_rules:
            status = "ACTIVE" if rule.is_active else "HISTORICAL"
            terms_info = (
                f"{len(rule.applies_to_terms)} specific terms" if rule.applies_to_terms else "All matching terms"
            )
            self.stdout.write(f"   • {rule.rule_name}: {rule.discount_percentage}% [{terms_info}] ({status})")
