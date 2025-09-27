"""
Setup time-of-day based discount rules.

This command creates discount rules that support different rates
for morning vs evening classes, as identified in the AR reconstruction
analysis for student 16516.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.finance.models.discounts import DiscountRule


class Command(BaseCommand):
    help = "Setup time-of-day based discount rules for the system"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what rules would be created without actually creating them",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        rules_to_create = [
            {
                "rule_name": "Morning Language 15%",
                "rule_type": "EARLY_BIRD",
                "pattern_text": "morning language classes",
                "discount_percentage": Decimal("15.00"),
                "applies_to_cycle": "LANG",
                "applies_to_schedule": {
                    "time_of_day": ["MORN"],
                    "cycles": ["LANG"],
                    "min_courses": 1,
                    "calculation_method": "per_class",
                    "description": "15% discount for morning Language program classes",
                },
                "is_active": True,
            },
            {
                "rule_name": "Evening Language 10%",
                "rule_type": "EARLY_BIRD",
                "pattern_text": "evening language classes",
                "discount_percentage": Decimal("10.00"),
                "applies_to_cycle": "LANG",
                "applies_to_schedule": {
                    "time_of_day": ["EVE"],
                    "cycles": ["LANG"],
                    "min_courses": 1,
                    "calculation_method": "per_class",
                    "description": "10% discount for evening Language program classes",
                },
                "is_active": True,
            },
            {
                "rule_name": "Morning BA 15%",
                "rule_type": "EARLY_BIRD",
                "pattern_text": "morning bachelor classes",
                "discount_percentage": Decimal("15.00"),
                "applies_to_cycle": "BA",
                "applies_to_schedule": {
                    "time_of_day": ["MORN"],
                    "cycles": ["BA"],
                    "min_courses": 1,
                    "calculation_method": "per_class",
                    "description": "15% discount for morning Bachelor program classes",
                },
                "is_active": True,
            },
            {
                "rule_name": "Evening BA 10%",
                "rule_type": "EARLY_BIRD",
                "pattern_text": "evening bachelor classes",
                "discount_percentage": Decimal("10.00"),
                "applies_to_cycle": "BA",
                "applies_to_schedule": {
                    "time_of_day": ["EVE"],
                    "cycles": ["BA"],
                    "min_courses": 1,
                    "calculation_method": "per_class",
                    "description": "10% discount for evening Bachelor program classes",
                },
                "is_active": True,
            },
            {
                "rule_name": "Mixed Schedule BA",
                "rule_type": "EARLY_BIRD",
                "pattern_text": "mixed morning evening bachelor",
                "discount_percentage": Decimal("12.50"),
                "applies_to_cycle": "BA",
                "applies_to_schedule": {
                    "time_of_day": ["MORN", "EVE"],
                    "cycles": ["BA"],
                    "min_courses": 2,
                    "calculation_method": "weighted_average",
                    "description": "Blended discount for BA students with both morning and evening classes",
                },
                "is_active": True,
            },
            {
                "rule_name": "Morning Masters 15%",
                "rule_type": "EARLY_BIRD",
                "pattern_text": "morning masters classes",
                "discount_percentage": Decimal("15.00"),
                "applies_to_cycle": "MASTERS",
                "applies_to_schedule": {
                    "time_of_day": ["MORN"],
                    "cycles": ["MASTERS"],
                    "min_courses": 1,
                    "calculation_method": "per_class",
                    "description": "15% discount for morning Masters program classes",
                },
                "is_active": True,
            },
            {
                "rule_name": "Evening Masters 10%",
                "rule_type": "EARLY_BIRD",
                "pattern_text": "evening masters classes",
                "discount_percentage": Decimal("10.00"),
                "applies_to_cycle": "MASTERS",
                "applies_to_schedule": {
                    "time_of_day": ["EVE"],
                    "cycles": ["MASTERS"],
                    "min_courses": 1,
                    "calculation_method": "per_class",
                    "description": "10% discount for evening Masters program classes",
                },
                "is_active": True,
            },
        ]

        if dry_run:
            self.stdout.write(self.style.SUCCESS("DRY RUN: Would create the following discount rules:"))
            for rule_data in rules_to_create:
                self.stdout.write(f"  - {rule_data['rule_name']}: {rule_data['discount_percentage']}%")
                self.stdout.write(f"    Time of day: {rule_data['applies_to_schedule']['time_of_day']}")
                self.stdout.write(f"    Cycle: {rule_data['applies_to_cycle']}")
                self.stdout.write("")
            return

        created_count = 0
        updated_count = 0

        for rule_data in rules_to_create:
            rule, created = DiscountRule.objects.update_or_create(rule_name=rule_data["rule_name"], defaults=rule_data)

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Created: {rule.rule_name}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"🔄 Updated: {rule.rule_name}"))

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"📊 Summary: {created_count} rules created, {updated_count} rules updated")
        )
        self.stdout.write("")
        self.stdout.write("🎯 Available time-of-day options: MORN, EVE, AFT")
        self.stdout.write("🎓 Available cycle options: LANG, BA, MASTERS")
        self.stdout.write("⚙️  Calculation methods: per_class, flat_rate, weighted_average")
