"""Simplified command to reconcile legacy payments from CSV data.

This command works directly with the legacy CSV files to perform reconciliation
without requiring the data to be loaded into the main database first.
"""

import csv
import logging
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)


class LegacyReconciliationCommand(BaseCommand):
    """Reconcile legacy payments directly from CSV files."""

    help = "Reconcile legacy payments using CSV data files (250728)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # File paths
        self.data_dir = Path("data/legacy")
        self.students_file = "all_students_250728.csv"
        self.payments_file = "all_receipt_headers_250728.csv"
        self.enrollments_file = "all_academiccoursetakers_250728.csv"
        self.classes_file = "all_academicclasses_250728.csv"

        # Data storage
        self.students = {}
        self.payments = []
        self.enrollments = defaultdict(list)  # by student_id
        self.classes = {}

        # Statistics
        self.stats = {
            "total_payments": 0,
            "reconciled": 0,
            "partial_match": 0,
            "unmatched": 0,
            "zero_payments": 0,
            "all_dropped": 0,
        }

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--data-dir",
            type=str,
            default="data/legacy",
            help="Directory containing CSV files",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="reconciliation_results.csv",
            help="Output CSV file for results",
        )
        parser.add_argument("--student-id", type=str, help="Process only specific student")
        parser.add_argument("--term", type=str, help="Process only specific term")
        parser.add_argument("--year", type=int, help="Process only specific year")
        parser.add_argument("--limit", type=int, help="Limit number of payments to process")

    def handle(self, *args, **options):
        """Main command handler."""

        self.data_dir = Path(options["data_dir"])

        try:
            # Load all data
            self.stdout.write("Loading data files...")
            self._load_students()
            self._load_classes()
            self._load_enrollments()
            self._load_payments()

            # Load pricing data from database
            self.stdout.write("Loading pricing data...")
            self._load_pricing_data()

            # Process payments
            self.stdout.write("Processing payments...")
            results = self._process_payments(options)

            # Write results
            self._write_results(results, options["output"])

            # Print summary
            self._print_summary()

        except Exception as e:
            logger.error(f"Error in legacy reconciliation: {e}")
            raise CommandError(f"Reconciliation failed: {e}") from e

    def _load_students(self):
        """Load student data."""
        filepath = self.data_dir / self.students_file

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                student_id = row.get("StudentID", "").zfill(5)
                self.students[student_id] = {
                    "first_name": row.get("FirstName", ""),
                    "last_name": row.get("LastName", ""),
                    "citizenship": row.get("Citizenship", ""),
                    "is_foreign": self._is_foreign(row.get("Citizenship", "")),
                }

        self.stdout.write(f"  Loaded {len(self.students):,} students")

    def _load_classes(self):
        """Load class data."""
        filepath = self.data_dir / self.classes_file

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                class_id = row.get("ClassID", "")
                self.classes[class_id] = {
                    "term_id": row.get("TermID", ""),
                    "course_code": row.get("CourseCode", ""),
                    "normalized_course": row.get("NormalizedCourse", ""),
                    "time_of_day": row.get("TimeOfDay", ""),
                    "section": row.get("Section", ""),
                    "normalized_part": row.get("NormalizedPart", ""),
                    "is_reading_class": self._is_reading_class(row),
                }

        self.stdout.write(f"  Loaded {len(self.classes):,} classes")

    def _load_enrollments(self):
        """Load enrollment data."""
        filepath = self.data_dir / self.enrollments_file

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                student_id = row.get("StudentID", "").zfill(5)
                class_id = row.get("ClassID", "")

                if class_id in self.classes:
                    enrollment = {
                        "class_id": class_id,
                        "term_id": row.get("TermID", ""),
                        "course_code": row.get("CourseCode", ""),
                        "normalized_course": row.get("NormalizedCourse", ""),
                        "attendance": row.get("Attendance", "Normal"),
                        "grade": row.get("Grade", ""),
                        "credits": Decimal(row.get("Credits", "3")),
                        "class_info": self.classes[class_id],
                    }
                    self.enrollments[student_id].append(enrollment)

        total_enrollments = sum(len(e) for e in self.enrollments.values())
        self.stdout.write(f"  Loaded {total_enrollments:,} enrollments")

    def _load_payments(self):
        """Load payment data."""
        filepath = self.data_dir / self.payments_file

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip deleted payments
                if row.get("Deleted") == "1":
                    continue

                student_id = row.get("StudentID", "").zfill(5)

                payment = {
                    "receipt_id": row.get("ReceiptID", ""),
                    "student_id": student_id,
                    "term_id": row.get("TermID", ""),
                    "amount": Decimal(row.get("Amount", "0")),
                    "payment_date": row.get("PaymentDate", ""),
                    "notes": row.get("Notes", ""),
                }
                self.payments.append(payment)

        self.stdout.write(f"  Loaded {len(self.payments):,} payments")

    def _load_pricing_data(self):
        """Load pricing data from database."""

        # This is a simplified version - you would load actual pricing data
        # from the DefaultPricing, CourseFixedPricing, etc. tables

        self.pricing = {
            "BA": {"domestic": Decimal("125"), "foreign": Decimal("150")},
            "MA": {"domestic": Decimal("175"), "foreign": Decimal("200")},
            "LANG": {
                "domestic": Decimal("100"),
                "foreign": Decimal("100"),
            },  # No foreign distinction
        }

        # Senior project courses
        self.senior_project_courses = {"IR-489", "BUS-489", "FIN-489", "THM-433"}

        # Reading class patterns
        self.reading_patterns = ["READ", "REQ", "SPECIAL"]

    def _is_foreign(self, citizenship: str) -> bool:
        """Determine if student is foreign."""
        if not citizenship:
            return False
        citizenship = citizenship.upper()
        return citizenship not in ["CAMBODIA", "CAMBODIAN", "KH", ""]

    def _is_reading_class(self, class_info: dict) -> bool:
        """Determine if a class is a reading class."""
        # Check normalized part for patterns
        normalized_part = class_info.get("NormalizedPart", "").upper()

        for pattern in self.reading_patterns:
            if pattern in normalized_part:
                return True

        return False

    def _get_cycle_from_course(self, course_code: str) -> str:
        """Determine cycle from course code."""
        if course_code.startswith(("EHSS", "IEAP", "GESL")):
            return "LANG"
        elif course_code.startswith(("MBA", "MED", "MIT")):
            return "MA"
        else:
            return "BA"

    def _calculate_expected_amount(self, enrollments: list[dict], is_foreign: bool) -> tuple[Decimal, str]:
        """Calculate expected payment amount for enrollments."""

        total = Decimal("0")
        details = []

        # Group by pricing type
        default_courses = []
        senior_projects = []
        reading_classes = []

        for enrollment in enrollments:
            # Skip dropped courses
            if enrollment["attendance"] == "Drop":
                continue

            course_code = enrollment["normalized_course"]

            if course_code in self.senior_project_courses:
                senior_projects.append(enrollment)
            elif enrollment["class_info"]["is_reading_class"]:
                reading_classes.append(enrollment)
            else:
                default_courses.append(enrollment)

        # Calculate default pricing
        if default_courses:
            # Group by cycle
            cycle_counts: defaultdict[str, int] = defaultdict(int)
            for e in default_courses:
                cycle = self._get_cycle_from_course(e["normalized_course"])
                cycle_counts[cycle] += 1

            for cycle, count in cycle_counts.items():
                price = self.pricing[cycle]["foreign" if is_foreign else "domestic"]
                total += price * count
                details.append(f"{count} {cycle} courses @ ${price}")

        # Add senior project pricing (simplified - assume highest tier)
        if senior_projects:
            # In reality, would need to determine tier
            sp_price = Decimal("300") if is_foreign else Decimal("250")
            total += sp_price * len(senior_projects)
            details.append(f"{len(senior_projects)} senior projects @ ${sp_price}")

        # Add reading class pricing (simplified)
        if reading_classes:
            rc_price = Decimal("200") if is_foreign else Decimal("175")
            total += rc_price * len(reading_classes)
            details.append(f"{len(reading_classes)} reading classes @ ${rc_price}")

        return total, "; ".join(details)

    def _process_payments(self, options) -> list[dict]:
        """Process all payments and return results."""

        results = []
        limit = options.get("limit")
        processed = 0

        for payment in self.payments:
            # Apply filters
            if options.get("student_id") and payment["student_id"] != options["student_id"]:
                continue

            if options.get("term") and payment["term_id"] != options["term"]:
                continue

            if options.get("year"):
                try:
                    payment_year = int(payment["payment_date"][:4])
                    if payment_year != options["year"]:
                        continue
                except (ValueError, TypeError, IndexError):
                    continue

            # Process payment
            result = self._reconcile_payment(payment)
            results.append(result)

            processed += 1
            if limit and processed >= limit:
                break

            if processed % 100 == 0:
                self.stdout.write(f"  Processed {processed:,} payments...")

        return results

    def _reconcile_payment(self, payment: dict) -> dict:
        """Reconcile a single payment."""

        self.stats["total_payments"] += 1

        student_id = payment["student_id"]
        student = self.students.get(student_id, {})
        student_name = f"{student.get('first_name', '')} {student.get('last_name', '')}"
        is_foreign = student.get("is_foreign", False)

        # Get enrollments for this term
        term_enrollments = [e for e in self.enrollments.get(student_id, []) if e["term_id"] == payment["term_id"]]

        # Handle zero payment
        if payment["amount"] == 0:
            self.stats["zero_payments"] += 1

            # Check if all courses dropped
            all_dropped = all(e["attendance"] == "Drop" for e in term_enrollments)

            if all_dropped:
                self.stats["all_dropped"] += 1
                status = "RECONCILED - All Dropped"
            else:
                status = "ZERO PAYMENT - Check"

            return {
                "receipt_id": payment["receipt_id"],
                "student_id": student_id,
                "student_name": student_name,
                "term_id": payment["term_id"],
                "payment_amount": payment["amount"],
                "expected_amount": Decimal("0"),
                "variance": Decimal("0"),
                "status": status,
                "confidence": "100%" if all_dropped else "0%",
                "details": (
                    f"{len(term_enrollments)} enrollments, all dropped"
                    if all_dropped
                    else "Zero payment with active enrollments"
                ),
                "matched_courses": "",
            }

        # Calculate expected amount
        expected_amount, pricing_details = self._calculate_expected_amount(term_enrollments, is_foreign)

        variance = abs(payment["amount"] - expected_amount)
        variance_pct = (variance / payment["amount"] * 100) if payment["amount"] > 0 else 0

        # Determine status
        if variance <= 1:  # Within $1
            self.stats["reconciled"] += 1
            status = "FULLY RECONCILED"
            confidence = "100%"
        elif variance_pct <= 5:  # Within 5%
            self.stats["reconciled"] += 1
            status = "RECONCILED - Minor Variance"
            confidence = "95%"
        elif variance_pct <= 10:  # Within 10%
            self.stats["partial_match"] += 1
            status = "PARTIAL MATCH"
            confidence = "85%"
        else:
            self.stats["unmatched"] += 1
            status = "UNMATCHED"
            confidence = "0%"

        # Get course list
        active_courses = [e["normalized_course"] for e in term_enrollments if e["attendance"] != "Drop"]

        return {
            "receipt_id": payment["receipt_id"],
            "student_id": student_id,
            "student_name": student_name,
            "term_id": payment["term_id"],
            "payment_amount": payment["amount"],
            "expected_amount": expected_amount,
            "variance": variance,
            "variance_pct": f"{variance_pct:.1f}%",
            "status": status,
            "confidence": confidence,
            "details": pricing_details,
            "matched_courses": ", ".join(active_courses),
            "is_foreign": "Y" if is_foreign else "N",
        }

    def _write_results(self, results: list[dict], filename: str):
        """Write results to CSV file."""

        self.stdout.write(f"Writing results to {filename}...")

        with open(filename, "w", newline="") as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)

        self.stdout.write(self.style.SUCCESS(f"Results written to {filename}"))

    def _print_summary(self):
        """Print reconciliation summary."""

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("LEGACY RECONCILIATION SUMMARY")
        self.stdout.write("=" * 60)

        total = self.stats["total_payments"]

        if total > 0:
            self.stdout.write(f"Total Payments: {total:,}")
            self.stdout.write("")

            self.stdout.write(
                f"Reconciled: {self.stats['reconciled']:,} ({self.stats['reconciled'] / total * 100:.1f}%)"
            )
            self.stdout.write(
                f"Partial Match: {self.stats['partial_match']:,} ({self.stats['partial_match'] / total * 100:.1f}%)"
            )
            self.stdout.write(f"Unmatched: {self.stats['unmatched']:,} ({self.stats['unmatched'] / total * 100:.1f}%)")
            self.stdout.write("")
            self.stdout.write(f"Zero Payments: {self.stats['zero_payments']:,}")
            self.stdout.write(f"All Courses Dropped: {self.stats['all_dropped']:,}")

            success_rate = self.stats["reconciled"] / total * 100
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"Success Rate: {success_rate:.1f}%"))

        self.stdout.write("=" * 60)
