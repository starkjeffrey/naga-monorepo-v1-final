"""
Extract Discount End Dates from Historical Notes

Analyzes historical receipt notes to extract early bird discount deadlines
and populate Term.discount_end_date fields for automatic discount system.
"""

import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.curriculum.models import Term
from apps.finance.models.ar_reconstruction import LegacyReceiptMapping


class Command(BaseCommand):
    """Extract discount end dates from historical notes to populate Term model."""

    help = "Analyze historical notes to extract discount deadlines for automatic discount system"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("--term", type=str, help="Analyze specific term only (e.g., 240109E)")
        parser.add_argument(
            "--output-file",
            type=str,
            default="project-docs/discount-dates/extracted_dates.txt",
            help="Output file for analysis results",
        )
        parser.add_argument(
            "--apply-changes",
            action="store_true",
            help="Apply extracted dates to Term.discount_end_date fields",
        )
        parser.add_argument(
            "--confidence-threshold",
            type=float,
            default=0.7,
            help="Minimum confidence score to apply date (0.0-1.0)",
        )

    def handle(self, *args, **options):
        """Main command execution."""
        self.stdout.write("📅 Starting discount date extraction from historical notes...")

        # Load historical receipt data
        if options["term"]:
            self.stdout.write(f"🎯 Analyzing term: {options['term']}")
            mappings = LegacyReceiptMapping.objects.filter(legacy_term_id=options["term"])
        else:
            self.stdout.write("📊 Analyzing all terms with legacy data...")
            mappings = LegacyReceiptMapping.objects.all()

        # Extract date information
        date_analysis = self.extract_discount_dates(mappings)

        # Generate recommendations
        recommendations = self.generate_recommendations(date_analysis, options["confidence_threshold"])

        # Output results
        self.output_analysis(date_analysis, recommendations, options["output_file"])

        # Apply changes if requested
        if options["apply_changes"]:
            self.apply_discount_dates(recommendations, options["confidence_threshold"])
        else:
            self.stdout.write("🔍 Dry run mode - use --apply-changes to update Term records")

        self.stdout.write("✅ Discount date extraction completed!")

    def extract_discount_dates(self, mappings) -> dict[str, dict]:
        """Extract discount-related date information from historical notes."""

        def _new_analysis() -> dict[str, Any]:
            return {
                "early_bird_mentions": [],
                "deadline_mentions": [],
                "payment_dates": [],
                "discount_dates": [],
                "patterns_found": [],
                "total_receipts": 0,
                "early_bird_receipts": 0,
            }

        term_analysis = defaultdict(_new_analysis)

        # Date extraction patterns
        date_patterns = [
            # Various date formats in notes
            r"(?:before|by|until|deadline)\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"(?:before|by|until|deadline)\s+(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{2,4})",
            r"(?:early|bird|registration).*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"pay\s+(?:before|by)\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"discount\s+(?:until|before|by)\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        ]

        # Early bird indicators
        early_bird_patterns = [
            r"early\s*bird",
            r"early\s*registration",
            r"early\s*payment",
            r"before\s+deadline",
            r"early\s*discount",
        ]

        self.stdout.write(f"🔍 Analyzing {mappings.count():,} receipt mappings...")

        for mapping in mappings:
            term_id = mapping.legacy_term_id
            notes = mapping.legacy_notes or ""

            if not notes.strip():
                continue

            analysis: dict[str, Any] = term_analysis[term_id]
            analysis["total_receipts"] += 1

            # Check for early bird mentions
            notes_lower = notes.lower()
            for pattern in early_bird_patterns:
                if re.search(pattern, notes_lower):
                    analysis["early_bird_mentions"].append(
                        {
                            "receipt_number": mapping.legacy_receipt_number,
                            "notes": notes,
                            "pattern": pattern,
                            "payment_date": self._extract_payment_date_from_receipt_id(mapping.legacy_receipt_id),
                        }
                    )
                    analysis["early_bird_receipts"] += 1
                    break

            # Extract date mentions
            for pattern in date_patterns:
                matches = re.finditer(pattern, notes, re.IGNORECASE)
                for match in matches:
                    date_str = match.group(1)
                    parsed_date = self._parse_date_string(date_str)
                    if parsed_date:
                        analysis["deadline_mentions"].append(
                            {
                                "receipt_number": mapping.legacy_receipt_number,
                                "date_string": date_str,
                                "parsed_date": parsed_date,
                                "notes": notes,
                                "pattern": pattern,
                            }
                        )

            # Extract payment date from receipt ID
            payment_date = self._extract_payment_date_from_receipt_id(mapping.legacy_receipt_id)
            if payment_date:
                analysis["payment_dates"].append(
                    {
                        "receipt_number": mapping.legacy_receipt_number,
                        "payment_date": payment_date,
                        "has_early_bird": any(re.search(p, notes_lower) for p in early_bird_patterns),
                    }
                )

        # Analyze patterns for each term
        for term_id, analysis in term_analysis.items():
            self._analyze_term_patterns(term_id, analysis)

        return dict(term_analysis)

    def _extract_payment_date_from_receipt_id(self, receipt_id: str) -> date | None:
        """Extract payment date from receipt ID format like 240109162323-clerk."""
        if not receipt_id:
            return None

        # Try to parse date from receipt ID format like 240109162323-clerk
        date_match = re.match(r"(\\d{6})", receipt_id)
        if date_match:
            date_str = date_match.group(1)
            if len(date_str) == 6:
                try:
                    # Format: YYMMDD -> 20YY-MM-DD
                    year = 2000 + int(date_str[:2])
                    month = int(date_str[2:4])
                    day = int(date_str[4:6])
                    return date(year, month, day)
                except (ValueError, TypeError):
                    pass

        return None

    def _parse_date_string(self, date_str: str) -> date | None:
        """Parse various date string formats."""
        date_str = date_str.strip()

        # Common date formats
        formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%m/%d/%y",
            "%m-%d-%y",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%Y-%m-%d",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                # Convert 2-digit years to 4-digit
                if parsed.year < 50:
                    parsed = parsed.replace(year=parsed.year + 2000)
                elif parsed.year < 100:
                    parsed = parsed.replace(year=parsed.year + 1900)

                return parsed.date()
            except ValueError:
                continue

        # Try month name formats
        month_patterns = [
            r"(\\d{1,2})\\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\\w*\\s+(\\d{2,4})",
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\\w*\\s+(\\d{1,2})\\s*,?\\s*(\\d{2,4})",
        ]

        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }

        for pattern in month_patterns:
            match = re.search(pattern, date_str.lower())
            if match:
                try:
                    if pattern.startswith("(\\\\d"):  # Day Month Year
                        day, month_str, year = match.groups()
                        month = month_map[month_str[:3]]
                        year = int(year)
                        day = int(day)
                    else:  # Month Day Year
                        month_str, day, year = match.groups()
                        month = month_map[month_str[:3]]
                        day = int(day)
                        year = int(year)

                    # Convert 2-digit years
                    if year < 50:
                        year += 2000
                    elif year < 100:
                        year += 1900

                    return date(year, month, day)
                except (ValueError, KeyError):
                    continue

        return None

    def _analyze_term_patterns(self, term_id: str, analysis: dict):
        """Analyze patterns for a specific term."""
        # Find most common deadline dates mentioned
        deadline_dates = [d["parsed_date"] for d in analysis["deadline_mentions"]]
        if deadline_dates:
            date_counter = Counter(deadline_dates)
            analysis["most_common_deadline"] = date_counter.most_common(1)[0]

        # Analyze payment dates for early bird patterns
        early_bird_payments = [
            p["payment_date"] for p in analysis["payment_dates"] if p["has_early_bird"] and p["payment_date"]
        ]
        regular_payments = [
            p["payment_date"] for p in analysis["payment_dates"] if not p["has_early_bird"] and p["payment_date"]
        ]

        if early_bird_payments and regular_payments:
            # Find the latest early bird payment and earliest regular payment
            latest_early_bird = max(early_bird_payments)
            earliest_regular = min(regular_payments)

            # Estimate deadline as between these dates
            if latest_early_bird < earliest_regular:
                # Calculate potential deadline
                diff_days = (earliest_regular - latest_early_bird).days
                estimated_deadline = latest_early_bird + timedelta(days=diff_days // 2)
                analysis["estimated_deadline"] = estimated_deadline
                analysis["deadline_confidence"] = min(
                    0.9,
                    len(early_bird_payments) / max(1, analysis["total_receipts"]) * 10,
                )

        # Calculate confidence scores
        analysis["patterns_confidence"] = self._calculate_pattern_confidence(analysis)

    def _calculate_pattern_confidence(self, analysis: dict) -> float:
        """Calculate confidence score for pattern analysis."""
        score = 0.0

        # Base score from sample size
        total_receipts = analysis["total_receipts"]
        if total_receipts > 0:
            score += min(0.3, total_receipts / 100)  # Up to 0.3 for sample size

        # Score from early bird mentions
        early_bird_ratio = analysis["early_bird_receipts"] / max(1, total_receipts)
        score += min(0.3, early_bird_ratio * 3)  # Up to 0.3 for early bird ratio

        # Score from explicit deadline mentions
        deadline_mentions = len(analysis["deadline_mentions"])
        score += min(0.2, deadline_mentions / 10)  # Up to 0.2 for deadline mentions

        # Score from payment date patterns
        payment_dates = len(analysis["payment_dates"])
        if payment_dates > 5:
            score += 0.2  # 0.2 for good payment date sample

        return min(1.0, score)

    def generate_recommendations(self, date_analysis: dict[str, dict], confidence_threshold: float) -> dict[str, dict]:
        """Generate recommendations for discount date configuration."""
        recommendations = {}

        for term_id, analysis in date_analysis.items():
            rec = {
                "term_id": term_id,
                "current_discount_date": None,
                "recommended_date": None,
                "confidence_score": analysis.get("patterns_confidence", 0.0),
                "evidence": [],
                "action": "no_action",
                "priority": "low",
            }

            # Check current Term configuration
            try:
                term = Term.objects.get(code=term_id)
                rec["current_discount_date"] = term.discount_end_date
                rec["term_exists"] = True
            except Term.DoesNotExist:
                rec["term_exists"] = False
                rec["action"] = "create_term"
                rec["priority"] = "high"
                recommendations[term_id] = rec
                continue

            # Analyze evidence
            evidence = []

            # Evidence from explicit deadline mentions
            if analysis.get("most_common_deadline"):
                deadline_date, count = analysis["most_common_deadline"]
                evidence.append(f"Explicit deadline mentioned {count} times: {deadline_date}")
                rec["recommended_date"] = deadline_date

            # Evidence from payment pattern analysis
            if analysis.get("estimated_deadline"):
                estimated = analysis["estimated_deadline"]
                evidence.append(f"Estimated from payment patterns: {estimated}")
                if not rec["recommended_date"]:
                    rec["recommended_date"] = estimated

            # Evidence from early bird mentions
            if analysis["early_bird_receipts"] > 0:
                ratio = analysis["early_bird_receipts"] / analysis["total_receipts"]
                evidence.append(
                    f"Early bird discount mentioned in {analysis['early_bird_receipts']} "
                    f"of {analysis['total_receipts']} receipts ({ratio:.1%})"
                )

            rec["evidence"] = evidence

            # Determine action and priority
            if rec["confidence_score"] >= confidence_threshold:
                if rec["current_discount_date"] is None:
                    rec["action"] = "set_discount_date"
                    rec["priority"] = "high"
                elif rec["recommended_date"] and rec["recommended_date"] != rec["current_discount_date"]:
                    rec["action"] = "update_discount_date"
                    rec["priority"] = "medium"
                else:
                    rec["action"] = "no_change_needed"
                    rec["priority"] = "low"
            else:
                rec["action"] = "insufficient_evidence"
                rec["priority"] = "low"

            recommendations[term_id] = rec

        return recommendations

    def output_analysis(
        self,
        date_analysis: dict[str, dict],
        recommendations: dict[str, dict],
        output_file: str,
    ):
        """Output analysis results to file and console."""
        import os

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("DISCOUNT DATE EXTRACTION ANALYSIS\\n")
            f.write("=" * 50 + "\\n\\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n")

            # Summary statistics
            total_terms = len(date_analysis)
            terms_with_evidence = len([t for t in recommendations.values() if t["confidence_score"] > 0.5])
            high_confidence = len([t for t in recommendations.values() if t["confidence_score"] > 0.7])

            f.write("SUMMARY STATISTICS\\n")
            f.write("-" * 20 + "\\n")
            f.write(f"Total terms analyzed: {total_terms}\\n")
            f.write(f"Terms with evidence: {terms_with_evidence}\\n")
            f.write(f"High confidence terms: {high_confidence}\\n\\n")

            # Recommendations by priority
            f.write("RECOMMENDATIONS BY PRIORITY\\n")
            f.write("-" * 30 + "\\n\\n")

            for priority in ["high", "medium", "low"]:
                priority_recs = [r for r in recommendations.values() if r["priority"] == priority]
                if priority_recs:
                    f.write(f"{priority.upper()} PRIORITY ({len(priority_recs)} terms):\\n")
                    f.write("-" * 20 + "\\n")

                    for rec in sorted(priority_recs, key=lambda x: x["confidence_score"], reverse=True):
                        f.write(f"\\nTerm {rec['term_id']}:\\n")
                        f.write(f"  Action: {rec['action']}\\n")
                        f.write(f"  Confidence: {rec['confidence_score']:.2f}\\n")

                        if rec["recommended_date"]:
                            f.write(f"  Recommended date: {rec['recommended_date']}\\n")

                        if rec["current_discount_date"]:
                            f.write(f"  Current date: {rec['current_discount_date']}\\n")

                        if rec["evidence"]:
                            f.write("  Evidence:\\n")
                            for evidence in rec["evidence"]:
                                f.write(f"    - {evidence}\\n")

                    f.write("\\n")

        self.stdout.write(f"📋 Analysis saved to: {output_file}")

        # Console summary
        self.stdout.write("\\n" + "=" * 60)
        self.stdout.write("📊 DISCOUNT DATE EXTRACTION SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total terms analyzed: {total_terms}")
        self.stdout.write(f"Terms with evidence: {terms_with_evidence}")
        self.stdout.write(f"High confidence recommendations: {high_confidence}")

        # Show top recommendations
        high_priority = [r for r in recommendations.values() if r["priority"] == "high"]
        if high_priority:
            self.stdout.write("\\n🔥 HIGH PRIORITY ACTIONS:")
            for rec in sorted(high_priority, key=lambda x: x["confidence_score"], reverse=True)[:5]:
                self.stdout.write(f"  • {rec['term_id']}: {rec['action']} (confidence: {rec['confidence_score']:.2f})")

    def apply_discount_dates(self, recommendations: dict[str, dict], confidence_threshold: float):
        """Apply recommended discount dates to Term records."""
        applied_count = 0
        skipped_count = 0

        self.stdout.write(f"🔄 Applying discount dates with confidence >= {confidence_threshold}...")

        with transaction.atomic():
            for term_id, rec in recommendations.items():
                if (
                    rec["confidence_score"] >= confidence_threshold
                    and rec["recommended_date"]
                    and rec["action"] in ["set_discount_date", "update_discount_date"]
                ):
                    try:
                        term = Term.objects.get(code=term_id)
                        old_date = term.discount_end_date
                        term.discount_end_date = rec["recommended_date"]
                        term.save(update_fields=["discount_end_date"])

                        applied_count += 1
                        self.stdout.write(
                            f"✅ {term_id}: {old_date} → {rec['recommended_date']} "
                            f"(confidence: {rec['confidence_score']:.2f})"
                        )

                    except Term.DoesNotExist:
                        self.stdout.write(f"❌ Term {term_id} not found")
                        skipped_count += 1

                    except Exception as e:
                        self.stdout.write(f"❌ Error updating {term_id}: {e}")
                        skipped_count += 1
                else:
                    skipped_count += 1

        self.stdout.write(f"\\n📊 Applied {applied_count} updates, skipped {skipped_count}")

        if applied_count > 0:
            self.stdout.write("\\n✅ Discount dates have been applied to Term records!")
            self.stdout.write("🔄 You can now use the automatic discount service.")
        else:
            self.stdout.write("\\n⚠️ No changes applied. Check confidence threshold or evidence quality.")
