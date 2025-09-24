"""Comprehensive analysis of legacy receipt data for enterprise-scale processing."""

import csv
import decimal
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.curriculum.models import Term
from apps.people.models import StudentProfile


class Command(BaseCommand):
    """Analyze 100K+ legacy receipts to identify patterns and required fixes."""

    help = "Enterprise-scale analysis of legacy receipt data - identifies all issues before processing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--receipt-file",
            type=str,
            default="data/legacy/all_receipt_headers_250728.csv",
            help="Path to receipt_headers CSV file",
        )

        parser.add_argument("--sample-size", type=int, help="Analyze only first N records (for testing)")

        parser.add_argument(
            "--generate-fixes",
            action="store_true",
            help="Generate automated fixing scripts for common issues",
        )

    def handle(self, *args, **options):
        """Execute comprehensive analysis of all legacy data."""
        self.stdout.write("🔍 Starting enterprise-scale legacy data analysis...")

        # Load and analyze all receipt data
        receipts = self._load_receipt_data(options["receipt_file"], options.get("sample_size"))

        self.stdout.write(f"📊 Analyzing {len(receipts):,} receipt records...")

        # Comprehensive analysis
        analysis_results = self._analyze_all_data(receipts)

        # Generate reports
        self._generate_executive_summary(analysis_results, len(receipts))
        self._generate_detailed_reports(analysis_results)

        # Generate automated fixing tools if requested
        if options["generate_fixes"]:
            self._generate_automated_fixes(analysis_results)

        self.stdout.write("✅ Analysis complete! Check project-docs/legacy-analysis/ for reports.")

    def _load_receipt_data(self, file_path: str, sample_size: int | None = None) -> list[dict]:
        """Load receipt data with progress tracking, excluding deleted records."""
        receipts: list[dict] = []
        deleted_count = 0
        csv_path = Path(file_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"Receipt file not found: {file_path}")

        self.stdout.write(f"📥 Loading data from {file_path}...")

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                # Skip deleted records (Deleted=1)
                if row.get("Deleted", "0").strip() == "1":
                    deleted_count += 1
                    continue

                if sample_size and len(receipts) >= sample_size:
                    break

                # Progress indicator for large datasets
                if i > 0 and i % 10000 == 0:
                    self.stdout.write(
                        f"   Loaded {len(receipts):,} valid records, skipped {deleted_count:,} deleted..."
                    )

                receipts.append(row)

        self.stdout.write(f"🗑️  Excluded {deleted_count:,} deleted records (Deleted=1)")
        return receipts

    def _safe_decimal(self, value) -> Decimal:
        """Safely convert a value to Decimal, returning 0 for invalid values."""
        try:
            if not value or str(value).strip().lower() in ["null", "none", ""]:
                return Decimal("0")
            return Decimal(str(value).strip())
        except (ValueError, TypeError, decimal.InvalidOperation):
            return Decimal("0")

    def _analyze_all_data(self, receipts: list[dict]) -> dict:
        """Comprehensive analysis of all receipt data."""
        self.stdout.write("🔬 Performing comprehensive data analysis...")

        analysis = {
            "total_records": len(receipts),
            "students": self._analyze_students(receipts),
            "terms": self._analyze_terms(receipts),
            "financial": self._analyze_financial_data(receipts),
            "data_quality": self._analyze_data_quality(receipts),
            "processing_estimates": {},
        }

        # Calculate processing estimates
        analysis["processing_estimates"] = self._calculate_processing_estimates(analysis)

        return analysis

    def _analyze_students(self, receipts: list[dict]) -> dict:
        """Analyze student data patterns."""
        self.stdout.write("   Analyzing student data...")

        unique_students = set()
        missing_students = []
        existing_students = []
        student_names = {}

        # Get all existing students for fast lookup
        existing_student_ids = set(StudentProfile.objects.values_list("student_id", flat=True))

        for receipt in receipts:
            student_id_raw = receipt.get("ID", "").strip()
            if not student_id_raw:
                continue

            try:
                student_id = int(student_id_raw.zfill(5))
                unique_students.add(student_id)
                student_names[student_id] = receipt.get("name", "Unknown")

                if student_id in existing_student_ids:
                    existing_students.append(student_id)
                else:
                    missing_students.append(
                        {
                            "student_id": student_id,
                            "name": receipt.get("name", "Unknown"),
                            "receipt_count": 0,  # Will be calculated separately
                        }
                    )
            except (ValueError, TypeError):
                continue

        # Count receipts per missing student
        missing_student_counts: Counter[int] = Counter()
        for receipt in receipts:
            student_id_raw = receipt.get("ID", "").strip()
            try:
                student_id = int(student_id_raw.zfill(5))
                if student_id not in existing_student_ids:
                    missing_student_counts[student_id] += 1
            except (ValueError, TypeError):
                continue

        # Update receipt counts
        for student_data in missing_students:
            student_data["receipt_count"] = missing_student_counts[student_data["student_id"]]

        return {
            "total_unique_students": len(unique_students),
            "existing_students": len(existing_students),
            "missing_students": len(missing_students),
            "missing_student_details": sorted(missing_students, key=lambda x: x["receipt_count"], reverse=True)[:100],
            "student_names": student_names,
        }

    def _analyze_terms(self, receipts: list[dict]) -> dict:
        """Analyze term data patterns."""
        self.stdout.write("   Analyzing term data...")

        term_counts: Counter[str] = Counter()
        unique_terms = set()

        for receipt in receipts:
            term_id = receipt.get("TermID", "").strip()
            if term_id and term_id != "NULL":
                unique_terms.add(term_id)
                term_counts[term_id] += 1

        # Check which terms exist in database
        existing_terms = set(Term.objects.values_list("code", flat=True))
        missing_terms = unique_terms - existing_terms

        return {
            "total_unique_terms": len(unique_terms),
            "existing_terms": len(existing_terms & unique_terms),
            "missing_terms": len(missing_terms),
            "term_counts": dict(term_counts.most_common(20)),
            "missing_term_list": list(missing_terms),
        }

    def _analyze_financial_data(self, receipts: list[dict]) -> dict:
        """Analyze financial data patterns."""
        self.stdout.write("   Analyzing financial data...")

        amounts = []
        payment_methods: Counter[str] = Counter()

        total_amount = Decimal("0")
        total_net_amount = Decimal("0")
        total_discounts = Decimal("0")

        for receipt in receipts:
            # Amount analysis with robust error handling
            try:
                # Clean and validate amount fields
                amount_str = str(receipt.get("Amount", "0") or "0").strip()
                net_amount_str = str(receipt.get("NetAmount", "0") or "0").strip()
                discount_str = str(receipt.get("NetDiscount", "0") or "0").strip()

                # Replace empty strings with '0'
                if not amount_str or amount_str.lower() in ["null", "none", ""]:
                    amount_str = "0"
                if not net_amount_str or net_amount_str.lower() in ["null", "none", ""]:
                    net_amount_str = "0"
                if not discount_str or discount_str.lower() in ["null", "none", ""]:
                    discount_str = "0"

                amount = Decimal(amount_str)
                net_amount = Decimal(net_amount_str)
                discount = Decimal(discount_str)

                amounts.append(float(net_amount))
                total_amount += amount
                total_net_amount += net_amount
                total_discounts += discount

            except (ValueError, TypeError, decimal.InvalidOperation):
                # Skip malformed financial data
                continue

            # Currency and payment method analysis
            payment_method = receipt.get("PmtType", "Unknown").strip()
            payment_methods[payment_method] += 1

        amounts.sort()

        return {
            "total_gross_amount": float(total_amount),
            "total_net_amount": float(total_net_amount),
            "total_discounts": float(total_discounts),
            "average_payment": sum(amounts) / len(amounts) if amounts else 0,
            "median_payment": amounts[len(amounts) // 2] if amounts else 0,
            "min_payment": min(amounts) if amounts else 0,
            "max_payment": max(amounts) if amounts else 0,
            "payment_methods": dict(payment_methods.most_common(10)),
            "records_with_discounts": sum(1 for r in receipts if self._safe_decimal(r.get("NetDiscount", "0")) > 0),
        }

    def _analyze_data_quality(self, receipts: list[dict]) -> dict:
        """Analyze data quality issues."""
        self.stdout.write("   Analyzing data quality...")

        quality_issues = {
            "missing_student_ids": 0,
            "missing_receipt_numbers": 0,
            "missing_amounts": 0,
            "missing_dates": 0,
            "invalid_dates": 0,
            "duplicate_receipts": 0,
            "malformed_data": 0,
        }

        receipt_numbers: Counter[str] = Counter()

        for receipt in receipts:
            # Check for missing critical fields
            if not receipt.get("ID", "").strip():
                quality_issues["missing_student_ids"] += 1

            if not receipt.get("ReceiptNo", "").strip():
                quality_issues["missing_receipt_numbers"] += 1

            if not receipt.get("NetAmount", "").strip():
                quality_issues["missing_amounts"] += 1

            if not receipt.get("PmtDate", "").strip():
                quality_issues["missing_dates"] += 1

            # Check for duplicate receipt numbers
            receipt_no = receipt.get("ReceiptNo", "").strip()
            if receipt_no:
                receipt_numbers[receipt_no] += 1

        # Count duplicates
        quality_issues["duplicate_receipts"] = sum(1 for count in receipt_numbers.values() if count > 1)

        return quality_issues

    def _calculate_processing_estimates(self, analysis: dict) -> dict:
        """Calculate processing time and complexity estimates."""
        total_records = analysis["total_records"]
        missing_students = analysis["students"]["missing_students"]
        missing_terms = analysis["terms"]["missing_terms"]

        # Estimate processing complexity
        complexity_score = 0
        if missing_students > total_records * 0.1:  # More than 10% missing students
            complexity_score += 3
        elif missing_students > 0:
            complexity_score += 1

        if missing_terms > 5:
            complexity_score += 2
        elif missing_terms > 0:
            complexity_score += 1

        # Estimate processing time (records per minute)
        base_speed = 100  # records per minute for clean data
        if complexity_score >= 4:
            processing_speed = 30
        elif complexity_score >= 2:
            processing_speed = 60
        else:
            processing_speed = base_speed

        estimated_time_minutes = total_records / processing_speed

        return {
            "complexity_score": complexity_score,
            "complexity_level": ("HIGH" if complexity_score >= 4 else "MEDIUM" if complexity_score >= 2 else "LOW"),
            "estimated_processing_speed": f"{processing_speed} records/minute",
            "estimated_total_time": f"{estimated_time_minutes / 60:.1f} hours",
            "recommended_batch_size": 1000 if complexity_score <= 2 else 500,
            "automation_potential": f"{max(0, 100 - missing_students / total_records * 100):.1f}%",
        }

    def _generate_executive_summary(self, analysis: dict, total_records: int):
        """Generate executive summary for decision makers."""
        summary_path = Path("project-docs/legacy-analysis/executive-summary.md")
        summary_path.parent.mkdir(parents=True, exist_ok=True)

        content = f"""# Legacy Data Analysis - Executive Summary

**Analysis Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total Records**: {total_records:,}

## Key Findings

### 🎯 Processing Readiness
- **Complexity Level**: {analysis["processing_estimates"]["complexity_level"]}
- **Automation Potential**: {analysis["processing_estimates"]["automation_potential"]}
- **Estimated Processing Time**: {analysis["processing_estimates"]["estimated_total_time"]}

### 📊 Data Overview
- **Unique Students**: {analysis["students"]["total_unique_students"]:,}
- **Existing Students**: {analysis["students"]["existing_students"]:,}
- **Missing Students**: {analysis["students"]["missing_students"]:,}
- **Financial Value**: ${analysis["financial"]["total_net_amount"]:,.2f}

### ⚠️ Critical Issues Requiring Attention
"""

        if analysis["students"]["missing_students"] > 0:
            content += (
                f"- **{analysis['students']['missing_students']:,} missing students** need to be created or mapped\n"
            )

        if analysis["terms"]["missing_terms"] > 0:
            content += f"- **{analysis['terms']['missing_terms']} missing terms** need to be created\n"

        if analysis["data_quality"]["duplicate_receipts"] > 0:
            content += (
                f"- **{analysis['data_quality']['duplicate_receipts']} duplicate receipts** need deduplication\n"
            )

        # Calculate discount rate to avoid long line
        total_discounts = analysis["financial"]["total_discounts"]
        total_gross = max(analysis["financial"]["total_gross_amount"], 1)
        discount_rate = total_discounts / total_gross * 100

        content += """
## Recommended Approach

1. **Automated Fixes**: Run bulk fixing tools to address """
        f"""{analysis["students"]["existing_students"]:,} processable records
2. **Manual Review**: Address {analysis["students"]["missing_students"]:,} missing students systematically
3. **Batch Processing**: Process in chunks of {analysis["processing_estimates"]["recommended_batch_size"]} records
4. **Quality Monitoring**: Monitor success rates and pause if below 80%

## Financial Impact
- **Total Value**: ${analysis["financial"]["total_net_amount"]:,.2f}
- **Average Payment**: ${analysis["financial"]["average_payment"]:.2f}
- **Discount Rate**: {discount_rate:.1f}%

---
*Generated by Legacy Data Analysis System*
"""

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.stdout.write(f"📋 Executive summary: {summary_path}")

    def _generate_detailed_reports(self, analysis: dict):
        """Generate detailed technical reports."""
        reports_dir = Path("project-docs/legacy-analysis")
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Missing students CSV
        students_csv = reports_dir / "missing-students-detailed.csv"
        with open(students_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Student_ID", "Student_Name", "Receipt_Count", "Priority"])

            for student in analysis["students"]["missing_student_details"]:
                priority = (
                    "HIGH" if student["receipt_count"] > 10 else "MEDIUM" if student["receipt_count"] > 5 else "LOW"
                )
                writer.writerow(
                    [
                        student["student_id"],
                        student["name"],
                        student["receipt_count"],
                        priority,
                    ]
                )

        # Missing terms report
        terms_report = reports_dir / "missing-terms.txt"
        with open(terms_report, "w", encoding="utf-8") as f:
            f.write("Missing Terms That Need Creation:\n")
            f.write("=" * 40 + "\n")
            for term in analysis["terms"]["missing_term_list"]:
                f.write(f"{term}\n")

        # Data quality report
        quality_report = reports_dir / "data-quality-issues.md"
        with open(quality_report, "w", encoding="utf-8") as f:
            f.write("# Data Quality Issues Report\n\n")
            for issue, count in analysis["data_quality"].items():
                if count > 0:
                    f.write(f"- **{issue.replace('_', ' ').title()}**: {count:,} records\n")

        self.stdout.write(f"📊 Detailed reports generated in: {reports_dir}")

    def _generate_automated_fixes(self, analysis: dict):
        """Generate automated fixing scripts."""
        scripts_dir = Path("project-docs/legacy-analysis/automated-fixes")
        scripts_dir.mkdir(parents=True, exist_ok=True)

        # Student creation script
        student_script = scripts_dir / "create_missing_students.py"
        with open(student_script, "w", encoding="utf-8") as f:
            f.write(
                '''#!/usr/bin/env python
"""Automated script to create missing students from legacy data."""

# This script would create PersonProfile and StudentProfile records
# for the missing students identified in the analysis.

# Usage: python manage.py shell < create_missing_students.py

from apps.people.models import PersonProfile, StudentProfile

# Add your student creation logic here
# Example:
# for student_data in missing_students:
#     person = PersonProfile.objects.create(...)
#     student = StudentProfile.objects.create(...)

print("Student creation script ready for implementation")
'''
            )

        self.stdout.write(f"🔧 Automated fixing scripts: {scripts_dir}")
