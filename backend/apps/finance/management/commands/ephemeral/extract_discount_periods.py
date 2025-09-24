"""
Extract clear discount periods with intended percentages for creating official discount rules.

This command focuses on:
1. Clean percentage rates (10%, 15%, 20%, 25%, 30%)
2. Clear start and end dates for discount periods
3. Number of students receiving each discount
"""

import csv
import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Extract clear discount periods for official rule creation."""

    help = "Extract discount periods with clean percentages and date ranges"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to legacy receipt headers CSV file")

        parser.add_argument(
            "--output-csv", type=str, default="discount_periods.csv", help="Output CSV with discount periods"
        )

        parser.add_argument(
            "--min-students", type=int, default=5, help="Minimum students to consider a discount period official"
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        output_csv = options["output_csv"]
        min_students = options["min_students"]

        self.stdout.write(self.style.SUCCESS(f"📊 Extracting discount periods from {csv_file}"))

        try:
            # Load and process data
            receipt_data = self._load_receipt_data(csv_file)
            self.stdout.write(f"📋 Loaded {len(receipt_data)} receipt records")

            # Extract discount periods by term
            discount_periods = self._extract_discount_periods(receipt_data, min_students)

            # Display results
            self._display_results(discount_periods)

            # Save to CSV
            self._save_csv(discount_periods, output_csv)
            self.stdout.write(self.style.SUCCESS(f"💾 Saved discount periods to {output_csv}"))

        except Exception as e:
            raise CommandError(f"Error extracting discount periods: {e}")

    def _load_receipt_data(self, csv_file: str) -> list[dict]:
        """Load receipt data focusing on records with discounts."""
        receipt_data = []

        with open(csv_file, encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    amount = Decimal(row.get("Amount", "0"))
                    net_amount = Decimal(row.get("NetAmount", "0"))
                except (ValueError, InvalidOperation):
                    continue

                # Only process records with discounts
                if amount <= 0 or net_amount <= 0 or amount <= net_amount:
                    continue

                # Parse payment date
                receipt_date = None
                pmt_date = row.get("PmtDate")
                if pmt_date:
                    try:
                        receipt_date = datetime.strptime(pmt_date.split(" ")[0], "%Y-%m-%d").date()
                    except ValueError:
                        continue

                if not receipt_date:
                    continue

                # Extract intended percentage from notes
                note = row.get("Notes", "").strip()
                percentages = self._extract_clean_percentages(note)

                if percentages:  # Only include if we found a percentage
                    receipt_data.append(
                        {
                            "ID": row.get("ID"),
                            "TermID": row.get("TermID", ""),
                            "Amount": amount,
                            "NetAmount": net_amount,
                            "Notes": note,
                            "receipt_date": receipt_date,
                            "intended_percentage": percentages[0],  # Primary percentage
                            "discount_type": self._classify_discount_type(note),
                        }
                    )

        return receipt_data

    def _extract_clean_percentages(self, note: str) -> list[int]:
        """Extract clean percentage values from notes."""
        percentages = []

        # Find percentage patterns
        percent_matches = re.findall(r"(\d+)\s*%", note)
        for match in percent_matches:
            try:
                percent = int(match)
                # Only include standard rates
                if percent in [5, 10, 15, 20, 25, 30, 50]:
                    percentages.append(percent)
            except ValueError:
                pass

        return percentages

    def _classify_discount_type(self, note: str) -> str:
        """Classify discount type for filtering."""
        note_lower = note.lower()

        # COVID patterns
        if any(term in note_lower for term in ["covid", "pandemic"]):
            return "COVID"

        # Early bird patterns
        early_indicators = ["pay by", "until", "before", "deadline", "all eng", "all ba", "all students"]
        if any(indicator in note_lower for indicator in early_indicators):
            return "EARLY_BIRD"

        # Special organizational discounts
        org_indicators = ["crst", "pepy", "jwoc", "adt", "alumni", "taprom", "sos"]
        if any(org in note_lower for org in org_indicators):
            return "ORGANIZATION"

        # Special identity discounts
        identity_indicators = ["monk", "staff", "teacher", "sibling"]
        if any(identity in note_lower for identity in identity_indicators):
            return "SPECIAL_IDENTITY"

        return "OTHER"

    def _extract_discount_periods(self, receipt_data: list[dict], min_students: int) -> dict:
        """Extract clear discount periods by term and percentage."""

        # Group by term
        terms_data = defaultdict(list)
        for receipt in receipt_data:
            term_id = receipt["TermID"]
            if term_id:
                terms_data[term_id].append(receipt)

        discount_periods = {}

        for term_id, receipts in terms_data.items():
            # Get term date range
            term_dates = [r["receipt_date"] for r in receipts]
            if not term_dates:
                continue

            term_start = min(term_dates)
            term_end = max(term_dates)

            # Group by percentage and type
            percentage_groups = defaultdict(list)
            for receipt in receipts:
                key = (receipt["intended_percentage"], receipt["discount_type"])
                percentage_groups[key].append(receipt)

            # Extract periods for each percentage
            term_periods = []
            for (percentage, discount_type), group_receipts in percentage_groups.items():
                if len(group_receipts) < min_students:
                    continue

                # Get date range for this discount
                discount_dates = sorted([r["receipt_date"] for r in group_receipts])
                period_start = discount_dates[0]
                period_end = discount_dates[-1]

                # Calculate period characteristics
                period_days = (period_end - period_start).days + 1
                term_days = (term_end - term_start).days + 1

                # Determine if it's early bird (short period) or full term
                is_early_bird = discount_type == "EARLY_BIRD" or (period_days <= 30 and period_days < term_days * 0.3)

                term_periods.append(
                    {
                        "percentage": percentage,
                        "discount_type": discount_type,
                        "period_start": period_start,
                        "period_end": period_end,
                        "student_count": len(group_receipts),
                        "total_discount_amount": sum(float(r["Amount"] - r["NetAmount"]) for r in group_receipts),
                        "period_days": period_days,
                        "is_early_bird": is_early_bird,
                        "sample_notes": [r["Notes"] for r in group_receipts[:3]],
                    }
                )

            if term_periods:
                discount_periods[term_id] = {
                    "term_start": term_start,
                    "term_end": term_end,
                    "periods": sorted(term_periods, key=lambda x: x["period_start"]),
                }

        return discount_periods

    def _display_results(self, discount_periods: dict):
        """Display extracted discount periods."""

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 DISCOUNT PERIODS FOR RULE CREATION"))
        self.stdout.write("=" * 80)

        # Sort terms chronologically
        sorted_terms = sorted(discount_periods.items(), key=lambda x: x[1]["term_start"])

        for term_id, data in sorted_terms:
            self.stdout.write(f"\n📚 TERM: {term_id}")
            self.stdout.write(f"   Full Term: {data['term_start']} to {data['term_end']}")

            for period in data["periods"]:
                percentage = period["percentage"]
                start = period["period_start"]
                end = period["period_end"]
                count = period["student_count"]
                amount = period["total_discount_amount"]
                dtype = period["discount_type"]
                days = period["period_days"]

                if period["is_early_bird"]:
                    period_type = f"EARLY ({days} days)"
                else:
                    period_type = f"EXTENDED ({days} days)"

                self.stdout.write(f"\n   💰 {percentage}% {dtype} - {period_type}")
                self.stdout.write(f"      Period: {start} to {end}")
                self.stdout.write(f"      Students: {count:,} | Total Discount: ${amount:,.2f}")
                if period["sample_notes"]:
                    sample = period["sample_notes"][0][:80]
                    self.stdout.write(f'      Sample: "{sample}..."')

    def _save_csv(self, discount_periods: dict, output_file: str):
        """Save discount periods to CSV for rule creation."""

        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            # Header
            writer.writerow(
                [
                    "TermID",
                    "TermStart",
                    "TermEnd",
                    "DiscountPercent",
                    "DiscountType",
                    "PeriodStart",
                    "PeriodEnd",
                    "PeriodDays",
                    "IsEarlyBird",
                    "StudentCount",
                    "TotalDiscountAmount",
                    "SampleNote",
                ]
            )

            # Sort and write data
            sorted_terms = sorted(discount_periods.items(), key=lambda x: x[1]["term_start"])

            for term_id, data in sorted_terms:
                for period in data["periods"]:
                    writer.writerow(
                        [
                            term_id,
                            data["term_start"],
                            data["term_end"],
                            period["percentage"],
                            period["discount_type"],
                            period["period_start"],
                            period["period_end"],
                            period["period_days"],
                            "YES" if period["is_early_bird"] else "NO",
                            period["student_count"],
                            f"{period['total_discount_amount']:.2f}",
                            period["sample_notes"][0][:200] if period["sample_notes"] else "",
                        ]
                    )
