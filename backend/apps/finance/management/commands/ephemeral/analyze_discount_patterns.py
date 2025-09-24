"""
Management command to analyze legacy discount patterns and infer discount rules.

This command processes legacy receipt data to automatically identify and classify
discount patterns, helping to populate the DiscountRule table for automatic
discount application.
"""

import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.finance.models.discounts import DiscountRule
from apps.finance.services.discount_pattern_inference import DiscountPatternInference


class Command(BaseCommand):
    """Analyze legacy discount patterns and create inferred discount rules."""

    help = "Analyze legacy receipt notes to infer discount patterns and create DiscountRule entries"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("csv_file", type=str, help="Path to legacy receipt headers CSV file")

        parser.add_argument(
            "--dry-run", action="store_true", help="Analyze patterns without creating DiscountRule entries"
        )

        parser.add_argument(
            "--min-confidence",
            type=float,
            default=0.6,
            help="Minimum confidence score to create rules (0.0-1.0, default: 0.6)",
        )

        parser.add_argument("--output-report", type=str, help="Path to save analysis report as CSV")

        parser.add_argument("--limit", type=int, help="Limit number of records to process (for testing)")

    def handle(self, *args, **options):
        """Execute the discount pattern analysis."""
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]
        min_confidence = options["min_confidence"]
        output_report = options.get("output_report")
        limit = options.get("limit")

        self.stdout.write(self.style.SUCCESS(f"🔍 Analyzing discount patterns from {csv_file}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("🧪 DRY RUN MODE - No DiscountRule entries will be created"))

        try:
            # Load and process legacy data
            receipt_data = self._load_receipt_data(csv_file, limit)
            self.stdout.write(f"📊 Loaded {len(receipt_data)} receipt records")

            # Initialize inference service
            inference_service = DiscountPatternInference()

            # Perform analysis
            self.stdout.write("🔬 Analyzing discount patterns...")
            analysis = inference_service.analyze_legacy_discount_patterns(receipt_data)

            # Display analysis results
            self._display_analysis_results(analysis)

            # Create discount rules if not dry run
            if not dry_run:
                created_rules = self._create_discount_rules(analysis["inferred_rules"], min_confidence)
                self.stdout.write(self.style.SUCCESS(f"✅ Created {created_rules} discount rules"))

            # Save report if requested
            if output_report:
                self._save_analysis_report(analysis, output_report)
                self.stdout.write(f"📋 Analysis report saved to {output_report}")

        except Exception as e:
            raise CommandError(f"Error analyzing discount patterns: {e}") from e

    def _load_receipt_data(self, csv_file: str, limit: int | None = None) -> list[dict]:
        """Load receipt data from CSV file."""
        receipt_data = []

        try:
            with open(csv_file, encoding="utf-8") as file:
                reader = csv.DictReader(file)

                for i, row in enumerate(reader):
                    if limit and i >= limit:
                        break

                    # Parse amounts
                    try:
                        amount = Decimal(row.get("Amount", "0"))
                        net_amount = Decimal(row.get("NetAmount", "0"))
                    except (InvalidOperation, ValueError):
                        continue  # Skip invalid amount records

                    # Parse receipt date
                    receipt_date = None
                    if row.get("ReceiptDate"):
                        try:
                            receipt_date = datetime.strptime(row["ReceiptDate"], "%Y-%m-%d").date()
                        except ValueError:
                            pass  # Keep as None if can't parse

                    receipt_data.append(
                        {
                            "IPK": row.get("IPK"),
                            "ReceiptNo": row.get("ReceiptNo"),
                            "ID": row.get("ID"),  # Student ID
                            "TermID": row.get("TermID"),
                            "Amount": amount,
                            "NetAmount": net_amount,
                            "NetDiscount": Decimal(row.get("NetDiscount", "0")),
                            "Notes": row.get("Notes", ""),
                            "receipt_date": receipt_date,
                        }
                    )

        except FileNotFoundError as e:
            raise CommandError(f"CSV file not found: {csv_file}") from e
        except Exception as e:
            raise CommandError(f"Error reading CSV file: {e}") from e

        return receipt_data

    def _display_analysis_results(self, analysis: dict):
        """Display analysis results in a formatted way."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 DISCOUNT PATTERN ANALYSIS RESULTS"))
        self.stdout.write("=" * 60)

        # Summary statistics
        total = analysis["total_receipts"]
        with_discounts = analysis["receipts_with_discounts"]
        discount_rate = (with_discounts / total * 100) if total > 0 else 0

        self.stdout.write(f"📋 Total receipts analyzed: {total:,}")
        self.stdout.write(f"💰 Receipts with discounts: {with_discounts:,} ({discount_rate:.1f}%)")

        # Confidence distribution
        conf_dist = analysis["confidence_distribution"]
        self.stdout.write("\n🎯 Confidence Distribution:")
        self.stdout.write(f"   High (≥80%): {conf_dist['high']:,}")
        self.stdout.write(f"   Medium (50-80%): {conf_dist['medium']:,}")
        self.stdout.write(f"   Low (<50%): {conf_dist['low']:,}")

        # Type distribution
        self.stdout.write("\n🏷️  Discount Type Distribution:")
        for discount_type, count in analysis["type_distribution"].items():
            self.stdout.write(f"   {discount_type}: {count:,}")

        # Top discount patterns
        self.stdout.write("\n🔝 Top Discount Patterns:")
        sorted_patterns = sorted(analysis["discount_patterns"].items(), key=lambda x: x[1]["count"], reverse=True)

        for pattern, data in sorted_patterns[:10]:
            total_discount = data["total_amount"]
            self.stdout.write(f"   {pattern}: {data['count']:,} times, ${total_discount:,.2f} total discount")

            # Show sample note
            if data["sample_notes"]:
                sample = data["sample_notes"][0][:60]
                self.stdout.write(f'      Sample: "{sample}..."')

        # Inferred rules
        high_conf_rules = [
            r for r in analysis["inferred_rules"] if r["processing_metadata"]["inference_confidence"] >= 0.6
        ]

        self.stdout.write("\n🤖 Inferred Discount Rules:")
        self.stdout.write(f"   Total inferred: {len(analysis['inferred_rules'])}")
        self.stdout.write(f"   High confidence (≥60%): {len(high_conf_rules)}")

        if high_conf_rules:
            self.stdout.write("\n📋 Sample High-Confidence Rules:")
            for rule in high_conf_rules[:5]:
                conf = rule["processing_metadata"]["inference_confidence"]
                self.stdout.write(f"   {rule['rule_name']} ({rule['rule_type']}) - Confidence: {conf:.1%}")

    def _create_discount_rules(self, inferred_rules: list[dict], min_confidence: float) -> int:
        """Create DiscountRule entries from inferred rules."""
        created_count = 0

        with transaction.atomic():
            for rule_config in inferred_rules:
                confidence = rule_config["processing_metadata"]["inference_confidence"]

                if confidence < min_confidence:
                    continue

                # Check if rule already exists
                existing_rule = DiscountRule.objects.filter(rule_name=rule_config["rule_name"]).first()

                if existing_rule:
                    self.stdout.write(self.style.WARNING(f"⚠️  Rule already exists: {rule_config['rule_name']}"))
                    continue

                # Create new rule
                try:
                    rule = DiscountRule.objects.create(
                        rule_name=rule_config["rule_name"],
                        rule_type=rule_config["rule_type"],
                        pattern_text=rule_config["pattern_text"],
                        discount_percentage=rule_config["discount_percentage"],
                        applies_to_cycle=rule_config["applies_to_cycle"],
                        applies_to_terms=rule_config["applies_to_terms"],
                        is_active=rule_config["is_active"],
                    )

                    created_count += 1

                    self.stdout.write(
                        f"✅ Created rule: {rule.rule_name} "
                        f"({rule.discount_percentage}% {rule.rule_type}) - "
                        f"Confidence: {confidence:.1%}"
                    )

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Error creating rule {rule_config['rule_name']}: {e}"))

        return created_count

    def _save_analysis_report(self, analysis: dict, output_file: str):
        """Save analysis report to CSV file."""
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)

                # Write summary
                writer.writerow(["DISCOUNT PATTERN ANALYSIS REPORT"])
                writer.writerow([f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
                writer.writerow([])

                # Summary statistics
                writer.writerow(["SUMMARY STATISTICS"])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Receipts", analysis["total_receipts"]])
                writer.writerow(["Receipts with Discounts", analysis["receipts_with_discounts"]])

                discount_rate = (
                    (analysis["receipts_with_discounts"] / analysis["total_receipts"] * 100)
                    if analysis["total_receipts"] > 0
                    else 0
                )
                writer.writerow(["Discount Rate %", f"{discount_rate:.1f}%"])
                writer.writerow([])

                # Discount patterns
                writer.writerow(["DISCOUNT PATTERNS"])
                writer.writerow(["Pattern", "Count", "Total Discount Amount", "Sample Note"])

                sorted_patterns = sorted(
                    analysis["discount_patterns"].items(), key=lambda x: x[1]["count"], reverse=True
                )

                for pattern, data in sorted_patterns:
                    sample_note = data["sample_notes"][0] if data["sample_notes"] else ""
                    writer.writerow(
                        [
                            pattern,
                            data["count"],
                            f"${data['total_amount']:.2f}",
                            sample_note[:100],  # Truncate long notes
                        ]
                    )

                writer.writerow([])

                # Inferred rules
                writer.writerow(["INFERRED DISCOUNT RULES"])
                writer.writerow(["Rule Name", "Type", "Percentage", "Confidence", "Active", "Pattern Text"])

                for rule in analysis["inferred_rules"]:
                    confidence = rule["processing_metadata"]["inference_confidence"]
                    writer.writerow(
                        [
                            rule["rule_name"],
                            rule["rule_type"],
                            f"{rule['discount_percentage']}%",
                            f"{confidence:.1%}",
                            rule["is_active"],
                            rule["pattern_text"],
                        ]
                    )

        except Exception as e:
            raise CommandError(f"Error saving report: {e}") from e
