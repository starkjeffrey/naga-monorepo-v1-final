"""
Migrate Discount Dates to Historical Terms

Creates a migration script to systematically populate Term.discount_end_date
fields based on historical analysis of receipt notes and payment patterns.
"""

import re
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.curriculum.models import Term
from apps.finance.models.ar_reconstruction import LegacyReceiptMapping
from apps.finance.services.automatic_discount_service import AutomaticDiscountService


class Command(BaseCommand):
    """Migrate discount dates to historical terms based on evidence."""

    help = "Populate Term.discount_end_date fields for historical terms based on legacy data analysis"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--confidence-threshold",
            type=float,
            default=0.7,
            help="Minimum confidence score to apply date (0.0-1.0)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without applying updates",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Apply changes even if confidence is below threshold",
        )
        parser.add_argument(
            "--output-file",
            type=str,
            default="project-docs/discount-migration/migration_results.txt",
            help="Output file for migration results",
        )
        parser.add_argument("--term", type=str, help="Process specific term only (e.g., 240109E)")

    def handle(self, *args, **options):
        """Main command execution."""
        self.stdout.write("🗓️ Starting discount date migration for historical terms...")

        # Initialize services
        self.discount_service = AutomaticDiscountService()

        # Analyze historical data
        if options["term"]:
            self.stdout.write(f"📊 Analyzing term: {options['term']}")
            migration_plan = self.analyze_term_discount_dates(options["term"])
        else:
            self.stdout.write("📊 Analyzing all historical terms...")
            migration_plan = self.analyze_all_terms_discount_dates()

        if not migration_plan:
            self.stdout.write(self.style.WARNING("⚠️ No discount date migration candidates found"))
            return

        # Filter by confidence
        filtered_plan = self.filter_migration_plan(migration_plan, options["confidence_threshold"], options["force"])

        # Show migration plan
        self.show_migration_summary(filtered_plan, options)

        # Apply migrations
        if not options["dry_run"]:
            applied_count = self.apply_migration_plan(filtered_plan)
            self.stdout.write(f"✅ Applied discount dates to {applied_count} terms")

            # Test automatic discount system
            self.test_automatic_discounts(filtered_plan)
        else:
            self.stdout.write("🔍 Dry run mode - no changes applied")

        # Generate report
        self.generate_migration_report(filtered_plan, options)

        self.stdout.write("🎉 Discount date migration completed!")

    def analyze_all_terms_discount_dates(self) -> dict[str, dict]:
        """Analyze discount dates for all terms with legacy data."""
        migration_plan = {}

        # Get all terms with legacy receipt data
        terms_with_data = LegacyReceiptMapping.objects.values_list("legacy_term_id", flat=True).distinct()

        total_terms = len(terms_with_data)
        self.stdout.write(f"🔍 Analyzing {total_terms} terms with legacy data...")

        for i, term_id in enumerate(terms_with_data, 1):
            if i % 10 == 0 or i == total_terms:
                self.stdout.write(f"  Progress: {i}/{total_terms} terms analyzed")

            term_analysis = self.analyze_term_discount_dates(term_id)
            if term_analysis:
                migration_plan.update(term_analysis)

        return migration_plan

    def analyze_term_discount_dates(self, term_id: str) -> dict[str, dict]:
        """Analyze discount dates for a specific term."""
        term_plan = {}

        # Check if term exists in system
        try:
            term = Term.objects.get(code=term_id)
        except Term.DoesNotExist:
            return {}

        # Skip if already has discount date
        if term.discount_end_date:
            return {}

        # Get legacy receipt data for this term
        receipts = (
            LegacyReceiptMapping.objects.filter(legacy_term_id=term_id)
            .exclude(legacy_notes__isnull=True)
            .exclude(legacy_notes__exact="")
        )

        if not receipts.exists():
            return {}

        # Analyze discount patterns
        analysis = self._extract_discount_evidence(receipts, term_id)

        if analysis["confidence_score"] > 0.3:  # Minimum evidence threshold
            term_plan[term_id] = {
                "term_object": term,
                "recommended_date": analysis["recommended_date"],
                "confidence_score": analysis["confidence_score"],
                "evidence": analysis["evidence"],
                "method": analysis["method"],
                "sample_size": analysis["sample_size"],
                "early_bird_mentions": analysis["early_bird_mentions"],
                "payment_pattern_data": analysis["payment_pattern_data"],
            }

        return term_plan

    def _extract_discount_evidence(self, receipts, term_id: str) -> dict:
        """Extract discount date evidence from receipt data."""
        evidence = {
            "recommended_date": None,
            "confidence_score": 0.0,
            "evidence": [],
            "method": "none",
            "sample_size": receipts.count(),
            "early_bird_mentions": 0,
            "payment_pattern_data": {},
        }

        # 1. Look for explicit deadline mentions in notes
        deadline_evidence = self._find_explicit_deadlines(receipts)
        if deadline_evidence["date"]:
            evidence.update(deadline_evidence)
            evidence["method"] = "explicit_deadline"
            return evidence

        # 2. Analyze early bird payment patterns
        pattern_evidence = self._analyze_payment_patterns(receipts, term_id)
        if pattern_evidence["date"]:
            evidence.update(pattern_evidence)
            evidence["method"] = "payment_pattern"
            return evidence

        # 3. Estimate based on term start date
        term_start_evidence = self._estimate_from_term_start(receipts, term_id)
        if term_start_evidence["date"]:
            evidence.update(term_start_evidence)
            evidence["method"] = "term_start_estimate"
            return evidence

        return evidence

    def _find_explicit_deadlines(self, receipts) -> dict:
        """Find explicit deadline mentions in receipt notes."""
        deadline_patterns = [
            r"(?:before|by|until|deadline)[\s:]*(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})",
            r"(?:early|bird|registration).*?(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})",
            r"discount[\s]*(?:until|before|by)[\s]*(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})",
            r"pay[\s]*(?:before|by)[\s]*(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})",
        ]

        found_dates = []
        early_bird_count = 0
        evidence_list = []

        for receipt in receipts:
            notes = receipt.legacy_notes or ""
            notes_lower = notes.lower()

            # Count early bird mentions
            if any(term in notes_lower for term in ["early bird", "early registration", "early payment"]):
                early_bird_count += 1

            # Look for date patterns
            for pattern in deadline_patterns:
                matches = re.finditer(pattern, notes, re.IGNORECASE)
                for match in matches:
                    date_str = match.group(1)
                    parsed_date = self._parse_date_string(date_str)
                    if parsed_date:
                        found_dates.append(parsed_date)
                        evidence_list.append(
                            f"Receipt {receipt.legacy_receipt_number}: '{date_str}' from '{notes[:50]}...'"
                        )

        if not found_dates:
            return {"date": None, "confidence_score": 0.0}

        # Find most common date
        from collections import Counter

        date_counter = Counter(found_dates)
        most_common_date, count = date_counter.most_common(1)[0]

        # Calculate confidence
        confidence = min(0.95, count / len(receipts) * 5 + 0.3)  # Base confidence + sample ratio
        if early_bird_count > 0:
            confidence += min(0.2, early_bird_count / len(receipts) * 3)

        return {
            "date": most_common_date,
            "confidence_score": confidence,
            "evidence": evidence_list[:5],  # Top 5 examples
            "early_bird_mentions": early_bird_count,
        }

    def _analyze_payment_patterns(self, receipts, term_id: str) -> dict:
        """Analyze payment timing patterns to estimate discount deadline."""
        early_bird_payments = []
        regular_payments = []
        evidence_list = []

        early_bird_indicators = [
            "early bird",
            "early registration",
            "early payment",
            "before deadline",
        ]

        for receipt in receipts:
            # Extract payment date from receipt ID (format: 240109162323-clerk)
            payment_date = self._extract_payment_date_from_receipt_id(receipt.legacy_receipt_id)
            if not payment_date:
                continue

            notes = (receipt.legacy_notes or "").lower()
            has_early_bird = any(indicator in notes for indicator in early_bird_indicators)

            if has_early_bird:
                early_bird_payments.append(payment_date)
            else:
                regular_payments.append(payment_date)

        if len(early_bird_payments) < 3 or len(regular_payments) < 3:
            return {"date": None, "confidence_score": 0.0}

        # Find the gap between early bird and regular payments
        latest_early_bird = max(early_bird_payments)
        earliest_regular = min(regular_payments)

        if latest_early_bird >= earliest_regular:
            return {"date": None, "confidence_score": 0.0}

        # Estimate deadline as midpoint or slightly after latest early bird
        gap_days = (earliest_regular - latest_early_bird).days
        if gap_days > 30:  # Too large gap, unreliable
            return {"date": None, "confidence_score": 0.0}

        # Estimate deadline
        estimated_deadline = latest_early_bird + timedelta(days=min(gap_days // 2, 5))

        # Calculate confidence based on pattern clarity
        early_bird_ratio = len(early_bird_payments) / len(receipts)
        confidence = min(0.8, early_bird_ratio * 2 + 0.2)

        evidence_list.append(f"Latest early bird payment: {latest_early_bird}")
        evidence_list.append(f"Earliest regular payment: {earliest_regular}")
        evidence_list.append(f"Gap: {gap_days} days")
        evidence_list.append(f"Early bird payments: {len(early_bird_payments)}")
        evidence_list.append(f"Regular payments: {len(regular_payments)}")

        return {
            "date": estimated_deadline,
            "confidence_score": confidence,
            "evidence": evidence_list,
            "early_bird_mentions": len(early_bird_payments),
            "payment_pattern_data": {
                "early_bird_payments": len(early_bird_payments),
                "regular_payments": len(regular_payments),
                "latest_early_bird": latest_early_bird,
                "earliest_regular": earliest_regular,
                "gap_days": gap_days,
            },
        }

    def _estimate_from_term_start(self, receipts, term_id: str) -> dict:
        """Estimate discount deadline based on term start date."""
        try:
            term = Term.objects.get(code=term_id)
            if not term.start_date:
                return {"date": None, "confidence_score": 0.0}
        except Term.DoesNotExist:
            return {"date": None, "confidence_score": 0.0}

        # Check if we have any early bird indicators
        early_bird_count = 0
        for receipt in receipts:
            notes = (receipt.legacy_notes or "").lower()
            if any(term in notes for term in ["early bird", "early registration", "early payment"]):
                early_bird_count += 1

        if early_bird_count == 0:
            return {"date": None, "confidence_score": 0.0}

        # Estimate deadline as 2 weeks before term start
        estimated_deadline = term.start_date - timedelta(days=14)

        # Low confidence since this is just an estimate
        confidence = min(0.5, early_bird_count / len(receipts) * 2)

        evidence = [
            f"Term start date: {term.start_date}",
            "Estimated deadline: 2 weeks before start",
            f"Early bird mentions: {early_bird_count}/{len(receipts)} receipts",
        ]

        return {
            "date": estimated_deadline,
            "confidence_score": confidence,
            "evidence": evidence,
            "early_bird_mentions": early_bird_count,
        }

    def _extract_payment_date_from_receipt_id(self, receipt_id: str) -> date | None:
        """Extract payment date from receipt ID format like 240109162323-clerk."""
        if not receipt_id:
            return None

        # Try to parse date from receipt ID format like 240109162323-clerk
        date_match = re.match(r"(\d{6})", receipt_id)
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

        return None

    def filter_migration_plan(
        self, migration_plan: dict[str, dict], confidence_threshold: float, force: bool
    ) -> dict[str, dict]:
        """Filter migration plan by confidence threshold."""
        if force:
            return migration_plan

        filtered_plan = {}
        for term_id, plan in migration_plan.items():
            if plan["confidence_score"] >= confidence_threshold:
                filtered_plan[term_id] = plan

        return filtered_plan

    def show_migration_summary(self, migration_plan: dict[str, dict], options):
        """Show migration summary."""
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("📊 DISCOUNT DATE MIGRATION SUMMARY")
        self.stdout.write("=" * 70)

        total_terms = len(migration_plan)
        if total_terms == 0:
            self.stdout.write("❌ No terms meet the confidence criteria for migration")
            return

        self.stdout.write(f"Terms to migrate: {total_terms}")
        self.stdout.write(f"Confidence threshold: {options['confidence_threshold']}")

        # Group by method
        methods = defaultdict(list)
        for term_id, plan in migration_plan.items():
            methods[plan["method"]].append((term_id, plan))

        for method, terms in methods.items():
            self.stdout.write(f"\n🔍 {method.upper().replace('_', ' ')} ({len(terms)} terms):")

            for term_id, plan in sorted(terms, key=lambda x: x[1]["confidence_score"], reverse=True)[:5]:
                self.stdout.write(
                    f"  • {term_id}: {plan['recommended_date']} (confidence: {plan['confidence_score']:.2f})"
                )

            if len(terms) > 5:
                self.stdout.write(f"    ... and {len(terms) - 5} more")

        # Show high confidence recommendations
        high_confidence = [
            (term_id, plan) for term_id, plan in migration_plan.items() if plan["confidence_score"] >= 0.8
        ]

        if high_confidence:
            self.stdout.write(f"\n🎯 HIGH CONFIDENCE RECOMMENDATIONS ({len(high_confidence)} terms):")
            for term_id, plan in sorted(high_confidence, key=lambda x: x[1]["confidence_score"], reverse=True)[:10]:
                self.stdout.write(
                    f"  ✅ {term_id}: {plan['recommended_date']} "
                    f"(confidence: {plan['confidence_score']:.2f}, method: {plan['method']})"
                )

    def apply_migration_plan(self, migration_plan: dict[str, dict]) -> int:
        """Apply the migration plan to update Term records."""
        applied_count = 0

        self.stdout.write(f"🔄 Applying discount dates to {len(migration_plan)} terms...")

        with transaction.atomic():
            for term_id, plan in migration_plan.items():
                try:
                    term = plan["term_object"]
                    old_date = term.discount_end_date
                    term.discount_end_date = plan["recommended_date"]
                    term.save(update_fields=["discount_end_date"])

                    applied_count += 1
                    self.stdout.write(
                        f"✅ {term_id}: {old_date} → {plan['recommended_date']} "
                        f"(confidence: {plan['confidence_score']:.2f})"
                    )

                except Exception as e:
                    self.stdout.write(f"❌ Error updating {term_id}: {e}")

        return applied_count

    def test_automatic_discounts(self, migration_plan: dict[str, dict]):
        """Test the automatic discount system with migrated terms."""
        self.stdout.write("\n🧪 Testing automatic discount system...")

        # Test a few terms with the automatic discount service
        test_terms = list(migration_plan.keys())[:3]

        for term_id in test_terms:
            try:
                summary = self.discount_service.get_term_discount_summary(term_id)

                if "error" not in summary:
                    status = summary.get("early_bird_status", "unknown")
                    days_until = summary.get("days_until_deadline", "N/A")

                    self.stdout.write(f"  📋 {term_id}: {status} (days until deadline: {days_until})")
                else:
                    self.stdout.write(f"  ❌ {term_id}: {summary['error']}")

            except Exception as e:
                self.stdout.write(f"  ❌ Error testing {term_id}: {e}")

    def generate_migration_report(self, migration_plan: dict[str, dict], options):
        """Generate detailed migration report."""
        import os

        output_file = options["output_file"]
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("DISCOUNT DATE MIGRATION REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Confidence threshold: {options['confidence_threshold']}\n")
            f.write(f"Dry run mode: {options['dry_run']}\n\n")

            # Summary statistics
            f.write("MIGRATION SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total terms migrated: {len(migration_plan)}\n")

            # Method breakdown
            methods = defaultdict(int)
            avg_confidence = 0
            for plan in migration_plan.values():
                methods[plan["method"]] += 1
                avg_confidence += plan["confidence_score"]

            if migration_plan:
                avg_confidence /= len(migration_plan)

            f.write(f"Average confidence: {avg_confidence:.2f}\n\n")

            f.write("METHOD BREAKDOWN\n")
            f.write("-" * 15 + "\n")
            for method, count in methods.items():
                f.write(f"{method.replace('_', ' ').title()}: {count}\n")
            f.write("\n")

            # Detailed results
            f.write("DETAILED RESULTS\n")
            f.write("-" * 15 + "\n\n")

            for term_id, plan in sorted(migration_plan.items()):
                f.write(f"Term {term_id}:\n")
                f.write(f"  Recommended date: {plan['recommended_date']}\n")
                f.write(f"  Confidence score: {plan['confidence_score']:.2f}\n")
                f.write(f"  Method: {plan['method']}\n")
                f.write(f"  Sample size: {plan['sample_size']} receipts\n")
                f.write(f"  Early bird mentions: {plan['early_bird_mentions']}\n")

                if plan["evidence"]:
                    f.write("  Evidence:\n")
                    for evidence in plan["evidence"]:
                        f.write(f"    - {evidence}\n")

                f.write("\n")

        self.stdout.write(f"📋 Migration report saved to: {output_file}")
