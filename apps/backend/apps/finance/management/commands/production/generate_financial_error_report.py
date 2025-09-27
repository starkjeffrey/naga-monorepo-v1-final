"""Generate comprehensive financial error report for A/R reconstruction.

This command analyzes the legacy receipt data and provides detailed error
categorization, impact assessment, and recommendations for the financial team.
"""

import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Term
from apps.people.models import StudentProfile


class Command(BaseMigrationCommand):
    """Generate comprehensive financial error report for leadership team."""

    help = "Generate detailed financial error analysis for A/R reconstruction"

    def execute_migration(self, *args, **options):
        """Execute the migration by delegating to handle method."""
        return self.handle(*args, **options)

    def get_rejection_categories(self):
        """Return rejection categories for analysis."""
        return {
            # Technical Data Quality Issues
            "NULL_CRITICAL_FIELDS": "Records with NULL ReceiptNo or ID fields",
            "STUDENT_NOT_FOUND": "Student not found in current system",
            "TERM_NOT_FOUND": "Term not found in current system",
            "NULL_TERM_DROPPED": "Records with NULL TermID (not deleted)",
            "DELETED_RECORDS_SKIPPED": "Records marked as deleted (Deleted=1)",
            "INVALID_FINANCIAL_DATA": "Invalid or unparseable financial amounts",
            "DUPLICATE_RECEIPTS_INFO": "Duplicate receipt numbers (handled automatically)",
            # Business Logic Issues
            "ENROLLMENT_MISSING": "Receipt exists but no enrollment record found",
            "PAYMENT_MISSING": "Enrollment exists but no payment received (uncollected)",
            "PARTIAL_PAYMENT": "Payment amount less than enrollment fee (underpayment)",
            "OVERPAYMENT": "Payment amount exceeds enrollment fee (overpayment)",
            "SCHOLARSHIP_MISMATCH": "Scholarship amount conflicts with payment records",
            "LATE_PAYMENT_PENALTY": "Payment includes late fees or penalties",
            "REFUND_REQUIRED": "Student withdrew but payment not refunded",
            # Processable Records
            "PROCESSABLE_RECORDS": "Valid records ready for processing",
        }

    def add_arguments(self, parser):
        parser.add_argument(
            "--receipt-file",
            type=str,
            default="data/legacy/all_receipt_headers_250728.csv",
            help="Path to receipt_headers CSV file",
        )

        parser.add_argument(
            "--output-dir",
            type=str,
            default="project-docs/financial-reports",
            help="Directory for output reports",
        )

        parser.add_argument(
            "--detailed",
            action="store_true",
            help="Generate detailed per-record analysis",
        )

    def handle(self, *args, **options):
        """Generate comprehensive financial error report."""
        self.output_dir = Path(options["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write("🔍 FINANCIAL ERROR ANALYSIS STARTING")
        self.stdout.write("=" * 60)

        # Load and analyze data
        self.load_receipt_data(options["receipt_file"])
        self.analyze_system_readiness()
        self.categorize_all_records()

        # Generate reports
        self.generate_executive_summary()
        self.generate_detailed_analysis(options["detailed"])
        self.generate_processing_recommendations()

        self.stdout.write(f"\n✅ Reports generated in: {self.output_dir}")

    def load_receipt_data(self, file_path: str):
        """Load receipt data with comprehensive analysis."""
        self.stdout.write(f"📥 Loading receipt data from {file_path}...")

        self.all_receipts = []
        self.deleted_receipts = []

        csv_path = Path(file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Receipt file not found: {file_path}")

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if row.get("Deleted", "0").strip() == "1":
                    self.deleted_receipts.append(row)
                else:
                    self.all_receipts.append(row)

                if i > 0 and i % 25000 == 0:
                    self.stdout.write(f"   Processed {i:,} total records...")

        self.stdout.write(f"✅ Loaded {len(self.all_receipts):,} active receipt records")
        self.stdout.write(f"🗑️  Found {len(self.deleted_receipts):,} deleted records")

    def analyze_system_readiness(self):
        """Analyze current system readiness for processing."""
        self.stdout.write("🏥 Analyzing system readiness...")

        # Student analysis
        self.student_count = StudentProfile.objects.count()
        self.students_by_id = {str(sp.student_id).zfill(5) for sp in StudentProfile.objects.only("student_id")}

        # Term analysis
        self.term_count = Term.objects.count()
        self.terms_by_code = set(Term.objects.values_list("code", flat=True))

        # Receipt number analysis
        self.receipt_numbers = Counter()
        for receipt in self.all_receipts:
            receipt_no = receipt.get("ReceiptNo", "").strip()
            if receipt_no and receipt_no != "NULL":
                self.receipt_numbers[receipt_no] += 1

        self.stdout.write(f"   ✅ {self.student_count:,} students available")
        self.stdout.write(f"   ✅ {self.term_count} terms available")
        duplicate_receipt_numbers = len([k for k, v in self.receipt_numbers.items() if v > 1])
        self.stdout.write(
            f"   i  {duplicate_receipt_numbers} duplicate receipt numbers (will be handled automatically)"
        )

    def categorize_all_records(self):
        """Categorize all records for comprehensive analysis."""
        self.stdout.write("📊 Categorizing all records...")

        self.categories = defaultdict(list)
        self.financial_totals = defaultdict(float)

        for i, receipt in enumerate(self.all_receipts):
            category = self.categorize_single_record(receipt, i + 1)
            self.categories[category].append(
                {
                    "record_num": i + 1,
                    "receipt_data": receipt,
                    "analysis": self.get_record_analysis(receipt),
                }
            )

            # Track financial impact
            try:
                amount = float(receipt.get("NetAmount", "0") or "0")
                self.financial_totals[category] += amount
            except (ValueError, TypeError):
                pass

        # Summary statistics
        total_records = len(self.all_receipts)
        len(self.categories["PROCESSABLE_RECORDS"])

        self.stdout.write("   📊 Categorization complete:")
        for category, records in self.categories.items():
            pct = (len(records) / total_records) * 100
            amount = self.financial_totals[category]
            self.stdout.write(f"      {category}: {len(records):,} ({pct:.1f}%) - ${amount:,.2f}")

    def categorize_single_record(self, receipt: dict, record_num: int) -> str:
        """Categorize a single record and return the category."""
        # Check for NULL critical fields
        receipt_no = receipt.get("ReceiptNo", "").strip()
        student_id = receipt.get("ID", "").strip()
        term_id = receipt.get("TermID", "").strip()

        if not receipt_no or receipt_no.upper() == "NULL":
            return "NULL_CRITICAL_FIELDS"

        if not student_id or student_id.upper() == "NULL":
            return "NULL_CRITICAL_FIELDS"

        # Check for NULL term
        if not term_id or term_id.upper() in ["NULL", "NONE", ""]:
            return "NULL_TERM_DROPPED"

        # Check student existence
        try:
            student_id_padded = str(int(student_id)).zfill(5)
            if student_id_padded not in self.students_by_id:
                return "STUDENT_NOT_FOUND"
        except (ValueError, TypeError):
            return "STUDENT_NOT_FOUND"

        # Check term existence
        if term_id not in self.terms_by_code:
            return "TERM_NOT_FOUND"

        # Check financial data validity
        try:
            amount = receipt.get("Amount", "0")
            net_amount = receipt.get("NetAmount", "0")
            if amount and amount != "NULL":
                float(amount)
            if net_amount and net_amount != "NULL":
                float(net_amount)
        except (ValueError, TypeError):
            return "INVALID_FINANCIAL_DATA"

        # All valid records are processable (duplicates handled by system)
        return "PROCESSABLE_RECORDS"

    def get_record_analysis(self, receipt: dict) -> dict:
        """Get detailed analysis for a record."""
        return {
            "student_id": receipt.get("ID", "").strip(),
            "term_id": receipt.get("TermID", "").strip(),
            "receipt_no": receipt.get("ReceiptNo", "").strip(),
            "amount": receipt.get("Amount", ""),
            "net_amount": receipt.get("NetAmount", ""),
            "payment_date": receipt.get("PmtDate", ""),
            "has_notes": bool(receipt.get("Notes", "").strip()),
            "student_name": receipt.get("name", "").strip(),
        }

    def generate_executive_summary(self):
        """Generate executive summary for financial team."""
        report_file = self.output_dir / f"executive_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("ACCOUNTS RECEIVABLE RECONSTRUCTION - EXECUTIVE SUMMARY\n")
            f.write("=" * 70 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Overall statistics
            total_records = len(self.all_receipts)
            deleted_records = len(self.deleted_receipts)
            processable = len(self.categories["PROCESSABLE_RECORDS"])

            f.write("OVERALL STATISTICS:\n")
            f.write("-" * 30 + "\n")
            f.write(f"Total Receipt Records: {total_records + deleted_records:,}\n")
            f.write(f"Active Records: {total_records:,}\n")
            f.write(f"Deleted Records (excluded): {deleted_records:,}\n")
            f.write(f"Records Ready for Processing: {processable:,}\n")
            f.write(f"Processing Success Rate Potential: {(processable / total_records) * 100:.1f}%\n\n")

            # Financial impact
            total_financial = sum(self.financial_totals.values())
            processable_financial = self.financial_totals["PROCESSABLE_RECORDS"]

            f.write("FINANCIAL IMPACT:\n")
            f.write("-" * 30 + "\n")
            f.write(f"Total Financial Value: ${total_financial:,.2f}\n")
            f.write(f"Processable Financial Value: ${processable_financial:,.2f}\n")
            f.write(f"At-Risk Financial Value: ${total_financial - processable_financial:,.2f}\n")
            f.write(f"Financial Recovery Rate: {(processable_financial / total_financial) * 100:.1f}%\n\n")

            # Duplicate handling information
            duplicate_receipt_numbers = len([k for k, v in self.receipt_numbers.items() if v > 1])
            duplicate_records = sum(v for k, v in self.receipt_numbers.items() if v > 1) - duplicate_receipt_numbers

            f.write("DUPLICATE HANDLING INFORMATION:\n")
            f.write("-" * 30 + "\n")
            f.write(f"Unique Receipt Numbers with Duplicates: {duplicate_receipt_numbers:,}\n")
            f.write(f"Total Records Requiring Hash Suffixes: {duplicate_records:,}\n")
            f.write("System automatically handles duplicates with hash suffixes\n")
            f.write("No manual intervention required for duplicate processing\n\n")

            # Error breakdown
            f.write("ERROR CATEGORY BREAKDOWN:\n")
            f.write("-" * 30 + "\n")
            for category, records in sorted(self.categories.items(), key=lambda x: len(x[1]), reverse=True):
                count = len(records)
                pct = (count / total_records) * 100
                financial = self.financial_totals[category]
                f.write(f"{category}: {count:,} records ({pct:.1f}%) - ${financial:,.2f}\n")

            f.write("\n")

            # Recommendations
            f.write("EXECUTIVE RECOMMENDATIONS:\n")
            f.write("-" * 30 + "\n")

            if processable >= total_records * 0.95:
                f.write("✅ HIGH CONFIDENCE: >95% of records are processable\n")
                f.write("   Recommend immediate full processing\n")
            elif processable >= total_records * 0.85:
                f.write("⚠️  MODERATE CONFIDENCE: 85-95% of records are processable\n")
                f.write("   Recommend processing with enhanced monitoring\n")
            else:
                f.write("🚨 LOW CONFIDENCE: <85% of records are processable\n")
                f.write("   Recommend addressing data quality issues first\n")

            f.write("\n")

            # Critical issues
            critical_issues = []
            if len(self.categories["STUDENT_NOT_FOUND"]) > total_records * 0.05:
                critical_issues.append("High rate of missing students (>5%)")
            if len(self.categories["TERM_NOT_FOUND"]) > 10:
                critical_issues.append("Missing terms detected")
            if len(self.categories["NULL_CRITICAL_FIELDS"]) > total_records * 0.01:
                critical_issues.append("Significant data quality issues (>1%)")

            if critical_issues:
                f.write("CRITICAL ISSUES REQUIRING ATTENTION:\n")
                f.write("-" * 30 + "\n")
                for issue in critical_issues:
                    f.write(f"🚨 {issue}\n")
            else:
                f.write("✅ NO CRITICAL ISSUES DETECTED\n")
                f.write("   System is ready for production processing\n")

        self.stdout.write(f"📄 Executive summary: {report_file}")

    def generate_detailed_analysis(self, include_detailed: bool):
        """Generate detailed technical analysis."""
        report_file = self.output_dir / f"detailed_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        with open(report_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Write header
            if include_detailed:
                writer.writerow(
                    [
                        "Record_Number",
                        "Category",
                        "Student_ID",
                        "Term_ID",
                        "Receipt_No",
                        "Amount",
                        "Net_Amount",
                        "Payment_Date",
                        "Student_Name",
                        "Has_Notes",
                        "Financial_Impact",
                    ]
                )

                # Write detailed records
                for category, records in self.categories.items():
                    for record_info in records:
                        analysis = record_info["analysis"]
                        try:
                            financial_impact = float(analysis["net_amount"] or "0")
                        except (ValueError, TypeError):
                            financial_impact = 0.0

                        writer.writerow(
                            [
                                record_info["record_num"],
                                category,
                                analysis["student_id"],
                                analysis["term_id"],
                                analysis["receipt_no"],
                                analysis["amount"],
                                analysis["net_amount"],
                                analysis["payment_date"],
                                analysis["student_name"],
                                "Yes" if analysis["has_notes"] else "No",
                                financial_impact,
                            ]
                        )
            else:
                # Write summary only
                writer.writerow(["Category", "Record_Count", "Percentage", "Financial_Impact"])
                total_records = len(self.all_receipts)

                for category, records in sorted(self.categories.items(), key=lambda x: len(x[1]), reverse=True):
                    count = len(records)
                    pct = (count / total_records) * 100
                    financial = self.financial_totals[category]
                    writer.writerow([category, count, f"{pct:.1f}%", f"${financial:,.2f}"])

        self.stdout.write(f"📊 Detailed analysis: {report_file}")

    def generate_processing_recommendations(self):
        """Generate processing recommendations and next steps."""
        report_file = self.output_dir / f"processing_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("PROCESSING RECOMMENDATIONS AND NEXT STEPS\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            processable = len(self.categories["PROCESSABLE_RECORDS"])
            total_records = len(self.all_receipts)

            f.write("IMMEDIATE ACTIONS:\n")
            f.write("-" * 30 + "\n")

            # Processing readiness
            if processable >= total_records * 0.95:
                f.write("1. ✅ PROCEED WITH FULL PROCESSING\n")
                f.write(f"   - {processable:,} records ready for immediate processing\n")
                f.write("   - Estimated processing time: 2-4 hours\n")
                f.write("   - Recommended batch size: 1,000 records\n")
            else:
                f.write("1. ⚠️  ADDRESS DATA QUALITY ISSUES FIRST\n")
                f.write("   - Review error categories below\n")
                f.write("   - Consider partial processing of valid records\n")

            f.write("\n")

            # Specific issue resolution
            f.write("ISSUE RESOLUTION PRIORITIES:\n")
            f.write("-" * 30 + "\n")

            priority = 1
            for category, records in sorted(self.categories.items(), key=lambda x: len(x[1]), reverse=True):
                if category == "PROCESSABLE_RECORDS":
                    continue

                count = len(records)
                if count == 0:
                    continue

                f.write(f"{priority}. {category}: {count:,} records\n")

                # Specific recommendations by category
                if category == "STUDENT_NOT_FOUND":
                    f.write("   - Review missing student IDs in detailed report\n")
                    f.write("   - Consider student data loading or ID mapping updates\n")
                elif category == "TERM_NOT_FOUND":
                    f.write("   - Create missing terms in system\n")
                    f.write("   - Verify term code mapping accuracy\n")
                elif category == "NULL_CRITICAL_FIELDS":
                    f.write("   - Review data export process\n")
                    f.write("   - These records likely cannot be processed\n")
                elif category == "DUPLICATE_RECEIPTS":
                    f.write("   - System will handle with hash suffixes\n")
                    f.write("   - No manual intervention required\n")
                elif category == "INVALID_FINANCIAL_DATA":
                    f.write("   - Review financial amount formats\n")
                    f.write("   - May require manual data correction\n")

                f.write("\n")
                priority += 1

            # Processing workflow
            f.write("RECOMMENDED PROCESSING WORKFLOW:\n")
            f.write("-" * 30 + "\n")
            f.write("Phase 1: Test Processing (Recommended)\n")
            f.write("  - Process 1,000 most recent records first\n")
            f.write("  - Validate results and financial accuracy\n")
            f.write("  - Adjust processing parameters if needed\n\n")

            f.write("Phase 2: Batch Processing\n")
            f.write("  - Process in 5,000-record batches\n")
            f.write("  - Monitor success rates and pause if < 80%\n")
            f.write("  - Generate progress reports every 10,000 records\n\n")

            f.write("Phase 3: Validation and Reconciliation\n")
            f.write("  - Compare reconstructed totals with legacy totals\n")
            f.write("  - Review variance reports\n")
            f.write("  - Manual review of high-variance records\n\n")

            # Quality assurance
            f.write("QUALITY ASSURANCE CHECKS:\n")
            f.write("-" * 30 + "\n")
            f.write("- Financial total reconciliation\n")
            f.write("- Student account balance verification\n")
            f.write("- Receipt number uniqueness validation\n")
            f.write("- Notes processing accuracy review\n")
            f.write("- Audit trail completeness check\n\n")

            # Risk assessment
            total_financial = sum(self.financial_totals.values())
            at_risk_financial = total_financial - self.financial_totals["PROCESSABLE_RECORDS"]

            f.write("RISK ASSESSMENT:\n")
            f.write("-" * 30 + "\n")
            f.write(f"Financial Value at Risk: ${at_risk_financial:,.2f}\n")
            f.write(f"Risk Percentage: {(at_risk_financial / total_financial) * 100:.1f}%\n")

            if at_risk_financial / total_financial < 0.05:
                f.write("Risk Level: LOW - Acceptable for processing\n")
            elif at_risk_financial / total_financial < 0.15:
                f.write("Risk Level: MODERATE - Monitor closely\n")
            else:
                f.write("Risk Level: HIGH - Address issues before processing\n")

        self.stdout.write(f"📋 Processing recommendations: {report_file}")
