"""Django management command to generate scholarship variance reports.

This command generates detailed reports of scholarship application variances
detected during reconciliation, providing insights into clerk accuracy and
system discrepancies for audit and quality control purposes.
"""

import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.finance.services.scholarship_reconciliation_service import ScholarshipVarianceReporter


class Command(BaseCommand):
    """Generate scholarship variance reports for audit and quality control."""

    help = "Generate scholarship variance reports with detailed analysis and recommendations"

    def add_arguments(self, parser):
        """Add command arguments."""

        parser.add_argument(
            "--date", type=str, help="Date for report generation (YYYY-MM-DD format, defaults to yesterday)"
        )

        parser.add_argument("--start-date", type=str, help="Start date for date range report (YYYY-MM-DD format)")

        parser.add_argument("--end-date", type=str, help="End date for date range report (YYYY-MM-DD format)")

        parser.add_argument(
            "--format",
            choices=["summary", "detailed", "json", "csv"],
            default="summary",
            help="Report format (default: summary)",
        )

        parser.add_argument("--output-file", type=str, help="Output file path (optional, defaults to stdout)")

        parser.add_argument(
            "--include-zero-variance", action="store_true", help="Include days with zero variances in range reports"
        )

    def handle(self, *args, **options):
        """Execute scholarship variance report generation."""

        # Parse date parameters
        if options["start_date"] and options["end_date"]:
            # Date range mode
            start_date = self._parse_date(options["start_date"])
            end_date = self._parse_date(options["end_date"])

            if start_date > end_date:
                raise CommandError("Start date must be before end date")

            report_data = self._generate_range_report(start_date, end_date, options["include_zero_variance"])

        elif options["date"]:
            # Single date mode
            target_date = self._parse_date(options["date"])
            report_data = ScholarshipVarianceReporter.generate_daily_variance_report(target_date)

        else:
            # Default to yesterday
            yesterday = timezone.now().date() - timedelta(days=1)
            report_data = ScholarshipVarianceReporter.generate_daily_variance_report(yesterday)

        # Generate output based on format
        if options["format"] == "summary":
            output = self._format_summary_report(report_data)
        elif options["format"] == "detailed":
            output = self._format_detailed_report(report_data)
        elif options["format"] == "json":
            output = json.dumps(report_data, indent=2, default=str)
        elif options["format"] == "csv":
            output = self._format_csv_report(report_data)

        # Output to file or stdout
        if options["output_file"]:
            output_path = Path(options["output_file"])
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)

            self.stdout.write(self.style.SUCCESS(f"✅ Report saved to: {output_path}"))
        else:
            self.stdout.write(output)

    def _parse_date(self, date_str: str) -> date:
        """Parse date string into date object."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as err:
            raise CommandError(f"Invalid date format: {date_str}. Use YYYY-MM-DD format.") from err

    def _generate_range_report(self, start_date: date, end_date: date, include_zero_variance: bool) -> dict:
        """Generate report for date range."""

        daily_reports = []
        current_date = start_date

        while current_date <= end_date:
            daily_report = ScholarshipVarianceReporter.generate_daily_variance_report(current_date)

            if include_zero_variance or daily_report["total_variances"] > 0:
                daily_reports.append(daily_report)

            current_date += timedelta(days=1)

        # Aggregate statistics
        total_variances = sum(report["total_variances"] for report in daily_reports)
        total_variance_amount = sum(report["total_variance_amount"] for report in daily_reports)
        total_payments = sum(report["total_scholarship_payments"] for report in daily_reports)

        avg_accuracy = 0
        if daily_reports:
            accuracy_rates = [r["clerk_accuracy_rate"] for r in daily_reports if r["total_scholarship_payments"] > 0]
            if accuracy_rates:
                avg_accuracy = sum(accuracy_rates) / len(accuracy_rates)

        return {
            "report_type": "range",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "summary": {
                "total_days": len(daily_reports),
                "total_variances": total_variances,
                "total_variance_amount": total_variance_amount,
                "total_scholarship_payments": total_payments,
                "average_accuracy_rate": round(avg_accuracy, 2),
            },
            "daily_reports": daily_reports,
        }

    def _format_summary_report(self, data: dict) -> str:
        """Format summary report for display."""

        if data.get("report_type") == "range":
            # Range report summary
            summary = data["summary"]
            output = []
            output.append("📊 SCHOLARSHIP VARIANCE REPORT - RANGE SUMMARY")
            output.append("=" * 60)
            output.append(f"Period: {data['start_date']} to {data['end_date']}")
            output.append(f"Days with data: {summary['total_days']}")
            output.append("")
            output.append("📈 AGGREGATE STATISTICS:")
            output.append(f"  Total scholarship payments: {summary['total_scholarship_payments']}")
            output.append(f"  Total variances detected: {summary['total_variances']}")
            output.append(f"  Total variance amount: ${summary['total_variance_amount']:.2f}")
            output.append(f"  Average clerk accuracy: {summary['average_accuracy_rate']:.1f}%")

            if summary["total_scholarship_payments"] > 0:
                variance_rate = (summary["total_variances"] / summary["total_scholarship_payments"]) * 100
                output.append(f"  Overall variance rate: {variance_rate:.1f}%")

        else:
            # Single day report
            output = []
            output.append("📊 SCHOLARSHIP VARIANCE REPORT - DAILY SUMMARY")
            output.append("=" * 60)
            output.append(f"Date: {data['date']}")
            output.append("")
            output.append("📈 VARIANCE STATISTICS:")
            output.append(f"  Total scholarship payments: {data['total_scholarship_payments']}")
            output.append(f"  Variances detected: {data['total_variances']}")
            output.append(f"  Total variance amount: ${data['total_variance_amount']:.2f}")
            output.append(f"  Clerk accuracy rate: {data['clerk_accuracy_rate']:.1f}%")
            output.append("")
            output.append("📋 VARIANCE BREAKDOWN:")
            categories = data["categories"]
            output.append(f"  Over-applied: {categories['overapplied']}")
            output.append(f"  Under-applied: {categories['underapplied']}")
            output.append(f"  Missing records: {categories['missing_records']}")
            output.append(f"  General variances: {categories['general_variances']}")

            # High priority items
            if data["high_priority_items"]:
                output.append("")
                output.append("🚨 HIGH PRIORITY ITEMS (≥$100 variance):")
                for item in data["high_priority_items"]:
                    output.append(f"  • {item['student_name']}: ${item['variance_amount']:.2f} ({item['type']})")

            # Recommendations
            if data["recommendations"]:
                output.append("")
                output.append("💡 RECOMMENDATIONS:")
                for rec in data["recommendations"]:
                    output.append(f"  • {rec}")

        return "\n".join(output)

    def _format_detailed_report(self, data: dict) -> str:
        """Format detailed report with full breakdown."""

        output = []

        if data.get("report_type") == "range":
            output.append("📊 DETAILED SCHOLARSHIP VARIANCE REPORT - DATE RANGE")
            output.append("=" * 80)
            output.append(f"Period: {data['start_date']} to {data['end_date']}")
            output.append("")

            # Summary section
            summary = data["summary"]
            output.append("📈 AGGREGATE SUMMARY:")
            output.append(f"  Days analyzed: {summary['total_days']}")
            output.append(f"  Total scholarship payments: {summary['total_scholarship_payments']}")
            output.append(f"  Total variances: {summary['total_variances']}")
            output.append(f"  Total variance amount: ${summary['total_variance_amount']:.2f}")
            output.append(f"  Average accuracy rate: {summary['average_accuracy_rate']:.1f}%")
            output.append("")

            # Daily breakdown
            output.append("📅 DAILY BREAKDOWN:")
            output.append("-" * 80)
            for report in data["daily_reports"]:
                if report["total_variances"] > 0:
                    output.append(
                        f"{report['date']}: {report['total_variances']} variances, "
                        f"${report['total_variance_amount']:.2f}, {report['clerk_accuracy_rate']:.1f}% accuracy"
                    )
        else:
            # Single day detailed report
            output.append("📊 DETAILED SCHOLARSHIP VARIANCE REPORT - DAILY")
            output.append("=" * 80)
            output.append(f"Date: {data['date']}")
            output.append("")

            # Statistics
            output.append("📈 DETAILED STATISTICS:")
            output.append(f"  Total scholarship payments processed: {data['total_scholarship_payments']}")
            output.append(f"  Variances detected: {data['total_variances']}")
            output.append(f"  Total variance amount: ${data['total_variance_amount']:.2f}")
            output.append(f"  Clerk accuracy rate: {data['clerk_accuracy_rate']:.1f}%")

            if data["total_scholarship_payments"] > 0:
                variance_rate = (data["total_variances"] / data["total_scholarship_payments"]) * 100
                output.append(f"  Variance detection rate: {variance_rate:.1f}%")

            # Category breakdown
            output.append("")
            output.append("📋 VARIANCE CATEGORIES:")
            categories = data["categories"]
            output.append(f"  Over-applied scholarships: {categories['overapplied']}")
            output.append(f"  Under-applied scholarships: {categories['underapplied']}")
            output.append(f"  Missing scholarship records: {categories['missing_records']}")
            output.append(f"  General variances: {categories['general_variances']}")

            # High priority items with details
            if data["high_priority_items"]:
                output.append("")
                output.append("🚨 HIGH PRIORITY ITEMS (≥$100 variance):")
                for item in data["high_priority_items"]:
                    output.append(f"  • Student: {item['student_name']}")
                    output.append(f"    Variance: ${item['variance_amount']:.2f}")
                    output.append(f"    Type: {item['type']}")
                    output.append(f"    Payment: {item['payment_reference']}")
                    output.append("")

            # Recommendations with context
            output.append("💡 DETAILED RECOMMENDATIONS:")
            for rec in data["recommendations"]:
                output.append(f"  • {rec}")

        return "\n".join(output)

    def _format_csv_report(self, data: dict) -> str:
        """Format report as CSV data."""

        if data.get("report_type") == "range":
            # Range report CSV
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow(
                [
                    "Date",
                    "Total_Payments",
                    "Variances",
                    "Variance_Amount",
                    "Accuracy_Rate",
                    "Overapplied",
                    "Underapplied",
                    "Missing_Records",
                ]
            )

            # Data rows
            for report in data["daily_reports"]:
                writer.writerow(
                    [
                        report["date"],
                        report["total_scholarship_payments"],
                        report["total_variances"],
                        f"{report['total_variance_amount']:.2f}",
                        f"{report['clerk_accuracy_rate']:.1f}",
                        report["categories"]["overapplied"],
                        report["categories"]["underapplied"],
                        report["categories"]["missing_records"],
                    ]
                )

            return output.getvalue()
        else:
            # Single day high-priority items CSV
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow(["Student_Name", "Payment_Reference", "Variance_Amount", "Variance_Type", "Date"])

            # High priority items
            for item in data["high_priority_items"]:
                writer.writerow(
                    [
                        item["student_name"],
                        item["payment_reference"],
                        f"{item['variance_amount']:.2f}",
                        item["type"],
                        data["date"],
                    ]
                )

            return output.getvalue()
