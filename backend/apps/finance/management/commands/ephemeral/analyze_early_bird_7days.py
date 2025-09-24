"""
Analyze 7-day early bird discount periods from term start dates.

This command:
1. Identifies the term start date (earliest receipt date)
2. Looks at receipts within first 10 days
3. Finds the most common discount rate during that period
4. Provides clear dates for creating discount rules
"""

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Extract 7-day early bird periods with most common discount rates."""

    help = "Analyze 7-day early bird discount rates from term start"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to legacy receipt headers CSV file")

        parser.add_argument(
            "--output-csv",
            type=str,
            default="early_bird_7day_analysis.csv",
            help="Output CSV with 7-day early bird analysis",
        )

        parser.add_argument(
            "--days-window", type=int, default=10, help="Days from term start to analyze (default: 10)"
        )

        parser.add_argument(
            "--min-receipts", type=int, default=5, help="Minimum receipts to consider rate significant"
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        output_csv = options["output_csv"]
        days_window = options["days_window"]
        min_receipts = options["min_receipts"]

        self.stdout.write(self.style.SUCCESS(f"📊 Analyzing 7-day early bird periods from {csv_file}"))

        try:
            # Load receipt data
            receipt_data = self._load_receipt_data(csv_file)
            self.stdout.write(f"📋 Loaded {len(receipt_data)} receipt records with discounts")

            # Analyze early bird periods by term
            early_bird_analysis = self._analyze_early_bird_periods(receipt_data, days_window, min_receipts)

            # Display results
            self._display_results(early_bird_analysis)

            # Save to CSV
            self._save_csv(early_bird_analysis, output_csv)
            self.stdout.write(self.style.SUCCESS(f"💾 Saved analysis to {output_csv}"))

        except Exception as e:
            raise CommandError(f"Error analyzing early bird periods: {e}") from e

    def _load_receipt_data(self, csv_file: str) -> list[dict]:
        """Load receipt data with discount information."""
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

                # Extract percentage from notes
                note = row.get("Notes", "").strip()
                percentages = self._extract_percentages(note)

                # Calculate actual discount
                discount_amount = amount - net_amount
                calculated_percent = round((discount_amount / amount) * 100, 1)

                receipt_data.append(
                    {
                        "ID": row.get("ID"),
                        "TermID": row.get("TermID", ""),
                        "receipt_date": receipt_date,
                        "Amount": amount,
                        "NetAmount": net_amount,
                        "DiscountAmount": discount_amount,
                        "calculated_percent": calculated_percent,
                        "intended_percent": percentages[0] if percentages else None,
                        "Notes": note,
                        "discount_type": self._classify_discount(note),
                    }
                )

        return receipt_data

    def _extract_percentages(self, note: str) -> list[int]:
        """Extract percentage values from note."""
        percentages = []

        # Find percentage patterns
        percent_matches = re.findall(r"(\d+)\s*%", note)
        for match in percent_matches:
            try:
                percent = int(match)
                if percent <= 50:  # Reasonable discount range
                    percentages.append(percent)
            except ValueError:
                pass

        return percentages

    def _classify_discount(self, note: str) -> str:
        """Classify discount type."""
        note_lower = note.lower()

        # Skip special identity discounts
        if any(term in note_lower for term in ["monk", "staff", "teacher", "sibling"]):
            return "SPECIAL_IDENTITY"

        # COVID discounts
        if any(term in note_lower for term in ["covid", "pandemic"]):
            return "COVID"

        # Early bird indicators
        early_indicators = ["pay by", "until", "before", "deadline", "all eng", "all ba", "for all"]
        if any(indicator in note_lower for indicator in early_indicators):
            return "EARLY_BIRD"

        # Organizational discounts
        org_indicators = ["crst", "pepy", "jwoc", "adt", "sos", "alumni"]
        if any(org in note_lower for org in org_indicators):
            return "ORGANIZATION"

        return "OTHER"

    def _analyze_early_bird_periods(self, receipt_data: list[dict], days_window: int, min_receipts: int) -> dict:
        """Analyze early bird periods for each term."""

        # Group by term
        terms_data = defaultdict(list)
        for receipt in receipt_data:
            term_id = receipt["TermID"]
            if term_id:
                terms_data[term_id].append(receipt)

        early_bird_analysis = {}

        for term_id, receipts in sorted(terms_data.items()):
            # Find term start date (earliest receipt)
            all_dates = [r["receipt_date"] for r in receipts]
            if not all_dates:
                continue

            term_start = min(all_dates)
            term_end = max(all_dates)
            early_bird_cutoff = term_start + timedelta(days=days_window)

            # Get receipts within early bird window
            early_bird_receipts = [
                r
                for r in receipts
                if r["receipt_date"] <= early_bird_cutoff and r["discount_type"] in ["EARLY_BIRD", "COVID", "OTHER"]
            ]

            if len(early_bird_receipts) < min_receipts:
                continue

            # Count discount rates (using intended rate if available)
            rate_counter: Counter[int] = Counter()
            rate_details = defaultdict(list)

            for receipt in early_bird_receipts:
                # Use intended percentage if found in notes, otherwise calculated
                rate = receipt["intended_percent"] or int(receipt["calculated_percent"])
                rate_counter[rate] += 1
                rate_details[rate].append(receipt)

            # Find most common rate
            if rate_counter:
                most_common_rate, count = rate_counter.most_common(1)[0]

                # Get date range for this rate
                rate_receipts = rate_details[most_common_rate]
                rate_dates = [r["receipt_date"] for r in rate_receipts]

                # Calculate suggested 7-day window
                suggested_start = term_start
                suggested_end = term_start + timedelta(days=7)

                # Count how many actually fall in 7-day window
                in_7day_window = sum(1 for r in rate_receipts if r["receipt_date"] <= suggested_end)

                early_bird_analysis[term_id] = {
                    "term_start": term_start,
                    "term_end": term_end,
                    "early_bird_cutoff": early_bird_cutoff,
                    "most_common_rate": most_common_rate,
                    "rate_count": count,
                    "total_early_bird": len(early_bird_receipts),
                    "rate_start": min(rate_dates),
                    "rate_end": max(rate_dates),
                    "suggested_7day_start": suggested_start,
                    "suggested_7day_end": suggested_end,
                    "receipts_in_7day": in_7day_window,
                    "sample_notes": [r["Notes"] for r in rate_receipts[:3]],
                    "all_rates": dict(rate_counter),
                    "total_discount_amount": sum(r["DiscountAmount"] for r in rate_receipts),
                }

        return early_bird_analysis

    def _display_results(self, analysis: dict):
        """Display analysis results."""

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 7-DAY EARLY BIRD DISCOUNT ANALYSIS"))
        self.stdout.write("=" * 80)

        # Sort by term chronologically
        sorted_terms = sorted(analysis.items(), key=lambda x: x[1]["term_start"])

        # Group by year for better visualization
        current_year = None

        for term_id, data in sorted_terms:
            year = data["term_start"].year
            if year != current_year:
                current_year = year
                self.stdout.write(f"\n{'=' * 40} YEAR {year} {'=' * 40}")

            self.stdout.write(f"\n📚 TERM: {term_id}")
            self.stdout.write(f"   Term Period: {data['term_start']} to {data['term_end']}")

            # Highlight the most common rate
            rate = data["most_common_rate"]
            count = data["rate_count"]
            total = data["total_early_bird"]
            percentage = (count / total * 100) if total > 0 else 0

            self.stdout.write(
                self.style.SUCCESS(f"\n   🎯 MOST COMMON RATE: {rate}% ({count}/{total} receipts = {percentage:.1f}%)")
            )

            # Show suggested 7-day period
            self.stdout.write(
                self.style.WARNING(
                    f"\n   📅 SUGGESTED 7-DAY PERIOD: {data['suggested_7day_start']} to {data['suggested_7day_end']}"
                )
            )
            self.stdout.write(f"      Receipts in 7-day window: {data['receipts_in_7day']}/{count}")

            # Show actual date range for this rate
            self.stdout.write(f"\n   📊 Actual {rate}% discount period: {data['rate_start']} to {data['rate_end']}")
            self.stdout.write(f"      Total discount given: ${data['total_discount_amount']:,.2f}")

            # Show all rates found
            if len(data["all_rates"]) > 1:
                self.stdout.write("\n   📈 All rates in early bird period:")
                for other_rate, other_count in sorted(data["all_rates"].items()):
                    if other_rate != rate:
                        self.stdout.write(f"      {other_rate}%: {other_count} receipts")

            # Show sample notes
            if data["sample_notes"]:
                self.stdout.write("\n   📝 Sample notes:")
                for i, note in enumerate(data["sample_notes"], 1):
                    sample = note[:80] + "..." if len(note) > 80 else note
                    self.stdout.write(f'      {i}. "{sample}"')

    def _save_csv(self, analysis: dict, output_file: str):
        """Save analysis to CSV."""

        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            # Header
            writer.writerow(
                [
                    "TermID",
                    "TermStart",
                    "TermEnd",
                    "MostCommonRate",
                    "RateCount",
                    "TotalEarlyBird",
                    "Suggested7DayStart",
                    "Suggested7DayEnd",
                    "ReceiptsIn7Day",
                    "ActualRateStart",
                    "ActualRateEnd",
                    "TotalDiscountAmount",
                    "AllRates",
                    "SampleNote",
                ]
            )

            # Sort and write data
            sorted_terms = sorted(analysis.items(), key=lambda x: x[1]["term_start"])

            for term_id, data in sorted_terms:
                # Format all rates as string
                all_rates_str = ", ".join(f"{rate}%:{count}" for rate, count in sorted(data["all_rates"].items()))

                writer.writerow(
                    [
                        term_id,
                        data["term_start"],
                        data["term_end"],
                        data["most_common_rate"],
                        data["rate_count"],
                        data["total_early_bird"],
                        data["suggested_7day_start"],
                        data["suggested_7day_end"],
                        data["receipts_in_7day"],
                        data["rate_start"],
                        data["rate_end"],
                        f"{data['total_discount_amount']:.2f}",
                        all_rates_str,
                        data["sample_notes"][0][:200] if data["sample_notes"] else "",
                    ]
                )
