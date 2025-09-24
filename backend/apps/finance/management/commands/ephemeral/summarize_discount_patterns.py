"""
Summarize discount patterns into simple, actionable recommendations for creating discount rules.

Groups patterns by era and provides clear recommendations.
"""

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Create simple discount pattern summary for rule creation."""

    help = "Summarize discount patterns for easy rule creation"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to legacy receipt headers CSV file")

        parser.add_argument(
            "--output-csv",
            type=str,
            default="discount_rules_summary.csv",
            help="Output CSV with discount rule recommendations",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        output_csv = options["output_csv"]

        self.stdout.write(self.style.SUCCESS("📊 Creating simple discount pattern summary"))

        try:
            # Load receipt data
            receipt_data = self._load_receipt_data(csv_file)
            self.stdout.write(f"📋 Loaded {len(receipt_data)} discount records")

            # Analyze patterns by year
            patterns_by_year = self._analyze_patterns_by_year(receipt_data)

            # Create recommendations
            recommendations = self._create_recommendations(patterns_by_year)

            # Display and save results
            self._display_recommendations(recommendations)
            self._save_recommendations(recommendations, output_csv)

        except Exception as e:
            raise CommandError(f"Error: {e}")

    def _load_receipt_data(self, csv_file: str) -> list[dict]:
        """Load and process receipt data."""
        receipt_data = []

        with open(csv_file, encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    amount = Decimal(row.get("Amount", "0"))
                    net_amount = Decimal(row.get("NetAmount", "0"))

                    if amount <= 0 or net_amount <= 0 or amount <= net_amount:
                        continue

                    # Parse date
                    pmt_date = row.get("PmtDate", "")
                    if not pmt_date:
                        continue

                    try:
                        receipt_date = datetime.strptime(pmt_date.split(" ")[0], "%Y-%m-%d").date()
                    except (ValueError, AttributeError, IndexError):
                        continue

                    # Extract percentage from notes
                    note = row.get("Notes", "").strip()
                    percentages = re.findall(r"(\d+)\s*%", note)

                    if percentages:
                        intended_percent = int(percentages[0])
                    else:
                        # Calculate percentage if not in notes
                        discount_amount = amount - net_amount
                        intended_percent = round((discount_amount / amount) * 100)

                    # Skip special identity discounts
                    note_lower = note.lower()
                    if any(term in note_lower for term in ["monk", "staff", "teacher", "sibling"]):
                        continue

                    receipt_data.append(
                        {
                            "TermID": row.get("TermID", ""),
                            "receipt_date": receipt_date,
                            "percentage": intended_percent,
                            "note": note,
                            "is_covid": "covid" in note_lower,
                            "is_early_bird": any(
                                term in note_lower
                                for term in ["pay by", "until", "before", "deadline", "all eng", "all ba"]
                            ),
                        }
                    )

                except (ValueError, ZeroDivisionError, TypeError):
                    continue

        return receipt_data

    def _analyze_patterns_by_year(self, receipt_data: list[dict]) -> dict:
        """Group and analyze patterns by year."""

        # Group by term
        terms_data = defaultdict(list)
        for receipt in receipt_data:
            term_id = receipt["TermID"]
            if term_id:
                terms_data[term_id].append(receipt)

        # Analyze each term
        patterns_by_year = defaultdict(list)

        for term_id, receipts in terms_data.items():
            if not receipts:
                continue

            # Get term dates
            dates = [r["receipt_date"] for r in receipts]
            term_start = min(dates)
            term_end = max(dates)
            year = term_start.year

            # Skip very old data
            if year < 2018:
                continue

            # Analyze discounts in first 10 days
            early_cutoff = term_start + timedelta(days=10)
            early_receipts = [r for r in receipts if r["receipt_date"] <= early_cutoff]

            if len(early_receipts) < 5:  # Need meaningful sample
                continue

            # Count percentages in early period
            early_percentages = Counter(r["percentage"] for r in early_receipts)
            most_common_percent, _count = early_percentages.most_common(1)[0]

            # Check if COVID period
            covid_count = sum(1 for r in receipts if r["is_covid"])
            is_covid_term = covid_count > len(receipts) * 0.2

            # Check if discount extends beyond early period
            late_receipts = [
                r for r in receipts if r["receipt_date"] > early_cutoff and r["percentage"] == most_common_percent
            ]
            is_full_term = len(late_receipts) > 10

            patterns_by_year[year].append(
                {
                    "term_id": term_id,
                    "term_start": term_start,
                    "term_end": term_end,
                    "most_common_percent": most_common_percent,
                    "early_receipt_count": len(early_receipts),
                    "total_receipt_count": len(receipts),
                    "is_covid_term": is_covid_term,
                    "is_full_term": is_full_term,
                    "sample_note": early_receipts[0]["note"] if early_receipts else "",
                }
            )

        return patterns_by_year

    def _create_recommendations(self, patterns_by_year: dict) -> list[dict]:
        """Create simple recommendations for discount rules."""

        recommendations = []

        for year in sorted(patterns_by_year.keys()):
            patterns = patterns_by_year[year]

            # Group by percentage
            percent_groups = defaultdict(list)
            for pattern in patterns:
                percent_groups[pattern["most_common_percent"]].append(pattern)

            # Create recommendation for each percentage
            for percentage, terms in percent_groups.items():
                # Skip rare percentages
                if len(terms) < 2:
                    continue

                # Determine pattern type
                covid_terms = [t for t in terms if t["is_covid_term"]]
                full_term_terms = [t for t in terms if t["is_full_term"]]
                early_bird_terms = [t for t in terms if not t["is_full_term"]]

                if covid_terms:
                    pattern_type = "COVID_FULL_TERM"
                    duration_desc = "Full term discount"
                elif len(full_term_terms) > len(early_bird_terms):
                    pattern_type = "FULL_TERM"
                    duration_desc = "Full term discount"
                else:
                    pattern_type = "EARLY_BIRD_7DAY"
                    duration_desc = "7-day early bird"

                # Get term list
                term_list = [t["term_id"] for t in terms]

                recommendations.append(
                    {
                        "year": year,
                        "percentage": percentage,
                        "pattern_type": pattern_type,
                        "duration_desc": duration_desc,
                        "term_count": len(terms),
                        "term_list": term_list,
                        "sample_terms": term_list[:3],  # First 3 as examples
                        "total_students": sum(t["early_receipt_count"] for t in terms),
                    }
                )

        return sorted(recommendations, key=lambda x: (x["year"], x["percentage"]))

    def _display_recommendations(self, recommendations: list[dict]):
        """Display recommendations in a simple format."""

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 SIMPLE DISCOUNT RULE RECOMMENDATIONS"))
        self.stdout.write("=" * 80)

        current_year = None

        for rec in recommendations:
            if rec["year"] != current_year:
                current_year = rec["year"]
                self.stdout.write(f"\n{'=' * 30} YEAR {current_year} {'=' * 30}")

            self.stdout.write(f"\n✅ {rec['percentage']}% {rec['duration_desc']}")
            self.stdout.write(f"   Terms: {rec['term_count']} terms ({rec['total_students']} students)")
            self.stdout.write(f"   Examples: {', '.join(rec['sample_terms'])}")

            if rec["pattern_type"] == "EARLY_BIRD_7DAY":
                self.stdout.write(
                    self.style.WARNING(
                        f"   → Create rule: {rec['percentage']}% discount, expires 7 days after term start"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"   → Create rule: {rec['percentage']}% discount, available entire term")
                )

    def _save_recommendations(self, recommendations: list[dict], output_file: str):
        """Save recommendations to CSV."""

        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            # Header
            writer.writerow(
                [
                    "Year",
                    "Percentage",
                    "PatternType",
                    "DurationDescription",
                    "TermCount",
                    "TotalStudents",
                    "ExampleTerms",
                    "AllTerms",
                ]
            )

            for rec in recommendations:
                writer.writerow(
                    [
                        rec["year"],
                        rec["percentage"],
                        rec["pattern_type"],
                        rec["duration_desc"],
                        rec["term_count"],
                        rec["total_students"],
                        ", ".join(rec["sample_terms"]),
                        ", ".join(rec["term_list"]),
                    ]
                )
