"""
Management command to analyze historical early bird discount rates per term.

This command processes legacy receipt data to extract:
- Discount percentages offered per term
- Date ranges when discounts were active
- Evolution from COVID full-term discounts to refined early bird periods
"""

import csv
import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Analyze historical discount rates and periods per term."""

    help = "Analyze legacy receipt data to extract historical discount rates and active periods per term"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("csv_file", type=str, help="Path to legacy receipt headers CSV file")

        parser.add_argument("--output-csv", type=str, help="Path to save results as CSV file")

        parser.add_argument("--output-detailed", type=str, help="Path to save detailed analysis with sample notes")

        parser.add_argument(
            "--min-occurrences",
            type=int,
            default=5,
            help="Minimum occurrences to consider a pattern significant (default: 5)",
        )

    def handle(self, *args, **options):
        """Execute the historical discount analysis."""
        csv_file = options["csv_file"]
        output_csv = options.get("output_csv")
        output_detailed = options.get("output_detailed")
        min_occurrences = options["min_occurrences"]

        self.stdout.write(self.style.SUCCESS(f"📊 Analyzing historical discount rates from {csv_file}"))

        try:
            # Load and process legacy data
            receipt_data = self._load_receipt_data(csv_file)
            self.stdout.write(f"📋 Loaded {len(receipt_data)} receipt records")

            # Analyze discount patterns by term
            term_analysis = self._analyze_discount_patterns_by_term(receipt_data, min_occurrences)

            # Display results
            self._display_results(term_analysis)

            # Save outputs if requested
            if output_csv:
                self._save_summary_csv(term_analysis, output_csv)
                self.stdout.write(f"💾 Summary saved to {output_csv}")

            if output_detailed:
                self._save_detailed_analysis(term_analysis, output_detailed)
                self.stdout.write(f"📋 Detailed analysis saved to {output_detailed}")

        except Exception as e:
            raise CommandError(f"Error analyzing historical discount rates: {e}") from e

    def _load_receipt_data(self, csv_file: str) -> list[dict]:
        """Load receipt data from CSV file."""
        receipt_data = []

        try:
            with open(csv_file, encoding="utf-8") as file:
                reader = csv.DictReader(file)

                for row in reader:
                    # Parse amounts
                    try:
                        amount = Decimal(row.get("Amount", "0"))
                        net_amount = Decimal(row.get("NetAmount", "0"))
                        net_discount = Decimal(row.get("NetDiscount", "0"))
                    except (InvalidOperation, ValueError):
                        continue  # Skip invalid amount records

                    # Only process records with discounts
                    if amount <= 0 or net_amount <= 0 or amount <= net_amount:
                        continue

                    # Parse receipt date (using PmtDate column)
                    receipt_date = None
                    pmt_date = row.get("PmtDate")
                    if pmt_date:
                        try:
                            # Handle datetime format from CSV: "2025-07-30 00:00:00.000"
                            receipt_date = datetime.strptime(pmt_date.split(" ")[0], "%Y-%m-%d").date()
                        except ValueError:
                            try:
                                receipt_date = datetime.strptime(pmt_date, "%m/%d/%Y").date()
                            except ValueError:
                                pass

                    if not receipt_date:
                        continue  # Skip records without valid dates

                    receipt_data.append(
                        {
                            "IPK": row.get("IPK"),
                            "ReceiptNo": row.get("ReceiptNo"),
                            "ID": row.get("ID"),  # Student ID
                            "TermID": row.get("TermID", ""),
                            "Amount": amount,
                            "NetAmount": net_amount,
                            "NetDiscount": net_discount,
                            "Notes": row.get("Notes", ""),
                            "receipt_date": receipt_date,
                        }
                    )

        except FileNotFoundError as e:
            raise CommandError(f"CSV file not found: {csv_file}") from e
        except Exception as e:
            raise CommandError(f"Error reading CSV file: {e}") from e

        return receipt_data

    def _analyze_discount_patterns_by_term(self, receipt_data: list[dict], min_occurrences: int) -> dict:
        """Analyze discount patterns grouped by term."""

        # Group receipts by term
        terms_data = defaultdict(list)
        for receipt in receipt_data:
            term_id = receipt["TermID"]
            if term_id:  # Skip empty term IDs
                terms_data[term_id].append(receipt)

        term_analysis = {}

        for term_id, receipts in terms_data.items():
            self.stdout.write(f"🔍 Analyzing term: {term_id}")

            # Extract discount patterns for this term
            discount_patterns = self._extract_discount_patterns(receipts)

            # Analyze date ranges and percentages
            term_summary = self._analyze_term_discount_summary(term_id, receipts, discount_patterns, min_occurrences)

            if term_summary:  # Only include terms with significant patterns
                term_analysis[term_id] = term_summary

        return term_analysis

    def _extract_discount_patterns(self, receipts: list[dict]) -> dict:
        """Extract discount patterns from receipt notes."""
        patterns: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "dates": [], "amounts": [], "sample_notes": [], "percentages": set()}
        )

        for receipt in receipts:
            note = receipt["Notes"].strip()
            amount = receipt["Amount"]
            net_amount = receipt["NetAmount"]
            receipt_date = receipt["receipt_date"]

            if not note or amount <= net_amount:
                continue

            # Calculate actual discount percentage
            discount_amount = amount - net_amount
            calculated_percentage = (discount_amount / amount) * 100
            calculated_percentage = round(calculated_percentage, 1)

            # Extract percentage mentions from notes (what clerk intended)
            note_percentages = self._extract_percentages_from_note(note)

            # Use intended percentage from note if found, otherwise calculated
            percentage: float | str
            if note_percentages:
                # Use the first percentage found in the note (clerk's intention)
                percentage = note_percentages[0]
            else:
                # Fall back to calculated percentage if no percentage in note
                percentage = calculated_percentage

            # Classify discount type
            discount_type = self._classify_discount_type(note, percentage, receipt_date)

            # Track pattern
            pattern_key = f"{discount_type}_{percentage}%"

            patterns[pattern_key]["count"] += 1
            patterns[pattern_key]["dates"].append(receipt_date)
            patterns[pattern_key]["amounts"].append(float(discount_amount))
            patterns[pattern_key]["percentages"].add(percentage)

            if len(patterns[pattern_key]["sample_notes"]) < 5:
                patterns[pattern_key]["sample_notes"].append(note)

        return patterns

    def _extract_percentages_from_note(self, note: str) -> list[float]:
        """Extract percentage values mentioned in notes."""
        percentages = []

        # Find percentage patterns
        percent_matches = re.findall(r"(\d+(?:\.\d+)?)\s*%", note)
        for match in percent_matches:
            try:
                percentages.append(float(match))
            except ValueError:
                pass

        return percentages

    def _classify_discount_type(self, note: str, percentage: float | str, receipt_date: date) -> str:
        """Classify discount type based on note content."""
        note_lower = note.lower()

        # COVID-era patterns
        if any(term in note_lower for term in ["covid", "pandemic", "emergency"]):
            return "COVID"

        # Early bird patterns
        early_bird_indicators = ["pay by", "early", "deadline", "before", "advance"]
        if any(indicator in note_lower for indicator in early_bird_indicators):
            return "EARLY_BIRD"

        # Mass discount patterns (likely early bird campaigns)
        mass_indicators = ["all students", "everyone", "students pay"]
        if any(indicator in note_lower for indicator in mass_indicators):
            return "EARLY_BIRD"

        # Special discounts
        special_indicators = ["monk", "staff", "employee", "sibling", "scholarship"]
        if any(indicator in note_lower for indicator in special_indicators):
            return "SPECIAL"

        # Time-based patterns (for variable rates)
        time_indicators = ["morning", "afternoon", "evening", "am", "pm", "time"]
        if any(indicator in note_lower for indicator in time_indicators):
            return "TIME_VARIABLE"

        # Default classification based on percentage and context
        if percentage >= 50:
            return "HIGH_SPECIAL"
        elif 10 <= percentage <= 25:
            return "LIKELY_EARLY_BIRD"
        else:
            return "OTHER"

    def _analyze_term_discount_summary(
        self, term_id: str, receipts: list[dict], patterns: dict, min_occurrences: int
    ) -> dict | None:
        """Analyze and summarize discount patterns for a term."""

        # Filter significant patterns
        significant_patterns = {k: v for k, v in patterns.items() if v["count"] >= min_occurrences}

        if not significant_patterns:
            return None

        # Extract term period info
        all_dates = [r["receipt_date"] for r in receipts]
        term_start = min(all_dates)
        term_end = max(all_dates)

        # Analyze early bird patterns specifically
        early_bird_patterns = {}
        variable_rate_detected = False

        for pattern_key, data in significant_patterns.items():
            if any(eb_type in pattern_key for eb_type in ["EARLY_BIRD", "COVID", "LIKELY_EARLY_BIRD"]):
                # Extract percentage from pattern key
                percentage_match = re.search(r"(\d+(?:\.\d+)?)%", pattern_key)
                if percentage_match:
                    percentage = float(percentage_match.group(1))

                    # Determine active period
                    discount_dates = sorted(data["dates"])
                    active_start = discount_dates[0]
                    active_end = discount_dates[-1]

                    # Check for variable rates
                    if len(data["percentages"]) > 1:
                        variable_rate_detected = True
                        percentage = "VARIABLE"

                    early_bird_patterns[percentage] = {
                        "count": data["count"],
                        "active_start": active_start,
                        "active_end": active_end,
                        "total_discount_amount": sum(data["amounts"]),
                        "sample_notes": data["sample_notes"][:3],
                        "pattern_type": pattern_key.split("_")[0],
                    }

            # Check for time-variable patterns
            if "TIME_VARIABLE" in pattern_key:
                variable_rate_detected = True

        # Determine discount offering pattern
        if not early_bird_patterns:
            return None

        # Analyze offering period
        offering_pattern = self._determine_offering_pattern(early_bird_patterns, term_start, term_end)

        return {
            "term_id": term_id,
            "term_start": term_start,
            "term_end": term_end,
            "early_bird_patterns": early_bird_patterns,
            "offering_pattern": offering_pattern,
            "variable_rates_detected": variable_rate_detected,
            "total_receipts": len(receipts),
            "total_discount_receipts": sum(p["count"] for p in early_bird_patterns.values()),
        }

    def _determine_offering_pattern(self, early_bird_patterns: dict, term_start: date, term_end: date) -> str:
        """Determine the discount offering pattern for the term."""

        if not early_bird_patterns:
            return "NO_EARLY_BIRD"

        # Get all active periods
        all_starts = [p["active_start"] for p in early_bird_patterns.values()]
        all_ends = [p["active_end"] for p in early_bird_patterns.values()]

        earliest_discount = min(all_starts)
        latest_discount = max(all_ends)

        # Calculate coverage
        discount_period_days = (latest_discount - earliest_discount).days + 1
        term_period_days = (term_end - term_start).days + 1
        coverage_ratio = discount_period_days / term_period_days if term_period_days > 0 else 0

        # Determine pattern
        if coverage_ratio >= 0.8:
            return "FULL_TERM"  # COVID-era pattern
        elif coverage_ratio <= 0.3:
            return "EARLY_PERIOD"  # Refined early bird
        else:
            return "EXTENDED_PERIOD"  # In-between

    def _display_results(self, term_analysis: dict):
        """Display analysis results."""

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 HISTORICAL DISCOUNT RATE ANALYSIS"))
        self.stdout.write("=" * 80)

        # Sort terms chronologically
        sorted_terms = sorted(term_analysis.items(), key=lambda x: x[1]["term_start"])

        for term_id, data in sorted_terms:
            self.stdout.write(f"\n🎓 TERM: {term_id}")
            self.stdout.write(f"   Period: {data['term_start']} to {data['term_end']}")
            self.stdout.write(f"   Pattern: {data['offering_pattern']}")

            if data["variable_rates_detected"]:
                self.stdout.write("   ⚠️  Variable rates detected (time-based)")

            self.stdout.write(
                f"   Receipts: {data['total_discount_receipts']:,} with discounts / {data['total_receipts']:,} total"
            )

            # Display early bird patterns
            for percentage, pattern_data in data["early_bird_patterns"].items():
                start_date = pattern_data["active_start"]
                end_date = pattern_data["active_end"]
                count = pattern_data["count"]
                total_discount = pattern_data["total_discount_amount"]
                pattern_type = pattern_data["pattern_type"]

                if percentage == "VARIABLE":
                    self.stdout.write(
                        f"   📈 VARIABLE% ({pattern_type}): {start_date} to {end_date} ({count:,} receipts, ${total_discount:,.2f})"
                    )
                else:
                    self.stdout.write(
                        f"   📈 {percentage}% ({pattern_type}): {start_date} to {end_date} ({count:,} receipts, ${total_discount:,.2f})"
                    )

                # Show sample note
                if pattern_data["sample_notes"]:
                    sample = pattern_data["sample_notes"][0][:60]
                    self.stdout.write(f'      Sample: "{sample}..."')

        # Summary statistics
        self.stdout.write("\n📊 SUMMARY:")
        self.stdout.write(f"   Terms analyzed: {len(term_analysis)}")

        # Pattern evolution
        covid_terms = sum(1 for data in term_analysis.values() if data["offering_pattern"] == "FULL_TERM")
        early_terms = sum(1 for data in term_analysis.values() if data["offering_pattern"] == "EARLY_PERIOD")

        self.stdout.write(f"   Full-term discount terms (COVID-era): {covid_terms}")
        self.stdout.write(f"   Early-period discount terms (refined): {early_terms}")

        variable_terms = sum(1 for data in term_analysis.values() if data["variable_rates_detected"])
        self.stdout.write(f"   Terms with variable rates: {variable_terms}")

    def _save_summary_csv(self, term_analysis: dict, output_file: str):
        """Save summary results to CSV."""
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow(
                    [
                        "TermID",
                        "TermStart",
                        "TermEnd",
                        "DiscountPercent",
                        "ActiveStart",
                        "ActiveEnd",
                        "OfferingPattern",
                        "ReceiptCount",
                        "TotalDiscountAmount",
                        "VariableRates",
                    ]
                )

                # Sort terms chronologically
                sorted_terms = sorted(term_analysis.items(), key=lambda x: x[1]["term_start"])

                for term_id, data in sorted_terms:
                    for percentage, pattern_data in data["early_bird_patterns"].items():
                        writer.writerow(
                            [
                                term_id,
                                data["term_start"],
                                data["term_end"],
                                percentage,
                                pattern_data["active_start"],
                                pattern_data["active_end"],
                                data["offering_pattern"],
                                pattern_data["count"],
                                f"{pattern_data['total_discount_amount']:.2f}",
                                "YES" if data["variable_rates_detected"] else "NO",
                            ]
                        )

        except Exception as e:
            raise CommandError(f"Error saving summary CSV: {e}") from e

    def _save_detailed_analysis(self, term_analysis: dict, output_file: str):
        """Save detailed analysis with sample notes."""
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow(
                    [
                        "TermID",
                        "DiscountPercent",
                        "PatternType",
                        "ActiveStart",
                        "ActiveEnd",
                        "ReceiptCount",
                        "TotalDiscountAmount",
                        "SampleNote1",
                        "SampleNote2",
                        "SampleNote3",
                    ]
                )

                # Sort terms chronologically
                sorted_terms = sorted(term_analysis.items(), key=lambda x: x[1]["term_start"])

                for term_id, data in sorted_terms:
                    for percentage, pattern_data in data["early_bird_patterns"].items():
                        sample_notes = pattern_data["sample_notes"] + ["", "", ""]  # Pad with empty strings

                        writer.writerow(
                            [
                                term_id,
                                percentage,
                                pattern_data["pattern_type"],
                                pattern_data["active_start"],
                                pattern_data["active_end"],
                                pattern_data["count"],
                                f"{pattern_data['total_discount_amount']:.2f}",
                                sample_notes[0][:100],  # Truncate long notes
                                sample_notes[1][:100],
                                sample_notes[2][:100],
                            ]
                        )

        except Exception as e:
            raise CommandError(f"Error saving detailed analysis: {e}") from e
