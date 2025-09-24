"""Management command to generate test fee reports for accounting.

This command generates comprehensive test fee reports for specific date ranges,
including G/L entries and payment summaries for integration with accounting systems.

Usage:
    python manage.py generate_test_fee_report --start-date 2025-01-01 --end-date 2025-01-31
    python manage.py generate_test_fee_report --month 2025-01
    python manage.py generate_test_fee_report --export-gl --start-date 2025-01-01 --end-date 2025-01-31
"""

import csv
import json
from datetime import date, datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.level_testing.finance_integration import TestFeeFinanceIntegrator


class Command(BaseCommand):
    help = "Generate test fee reports for accounting purposes"

    def add_arguments(self, parser):
        parser.add_argument("--start-date", type=str, help="Start date for report (YYYY-MM-DD format)")
        parser.add_argument("--end-date", type=str, help="End date for report (YYYY-MM-DD format)")
        parser.add_argument(
            "--month",
            type=str,
            help="Month for report (YYYY-MM format, alternative to start/end dates)",
        )
        parser.add_argument("--export-gl", action="store_true", help="Export G/L entries as CSV")
        parser.add_argument(
            "--output-dir",
            type=str,
            default="./reports",
            help="Output directory for report files",
        )
        parser.add_argument(
            "--format",
            type=str,
            choices=["json", "csv", "both"],
            default="json",
            help="Output format for reports",
        )

    def handle(self, *args, **options):
        # Parse date arguments
        start_date, end_date = self.parse_dates(options)

        self.stdout.write(self.style.SUCCESS(f"Generating test fee report for {start_date} to {end_date}"))

        # Create output directory
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(exist_ok=True)

        # Generate report
        integrator = TestFeeFinanceIntegrator()
        report_data = integrator.generate_test_fee_report(start_date, end_date)

        # Display summary
        self.display_summary(report_data)

        # Export report files
        self.export_reports(report_data, output_dir, options)

        # Export G/L entries if requested
        if options["export_gl"]:
            self.export_gl_entries(integrator, start_date, end_date, output_dir)

    def parse_dates(self, options):
        """Parse and validate date arguments."""
        if options["month"]:
            try:
                year, month = map(int, options["month"].split("-"))
                start_date = date(year, month, 1)

                # Calculate last day of month
                end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
                # Go back one day to get last day of target month
                end_date = date(end_date.year, end_date.month, end_date.day - 1)

            except ValueError as e:
                msg = "Invalid month format. Use YYYY-MM."
                raise CommandError(msg) from e

        elif options["start_date"] and options["end_date"]:
            try:
                start_date = datetime.strptime(options["start_date"], "%Y-%m-%d").date()
                end_date = datetime.strptime(options["end_date"], "%Y-%m-%d").date()
            except ValueError as e:
                msg = "Invalid date format. Use YYYY-MM-DD."
                raise CommandError(msg) from e

        else:
            # Default to current month
            now = timezone.now().date()
            start_date = date(now.year, now.month, 1)
            end_date = date(now.year + 1, 1, 1) if now.month == 12 else date(now.year, now.month + 1, 1)
            end_date = date(end_date.year, end_date.month, end_date.day - 1)

            self.stdout.write(
                self.style.WARNING(f"No dates specified, using current month: {start_date} to {end_date}"),
            )

        if start_date > end_date:
            msg = "Start date must be before end date."
            raise CommandError(msg)

        return start_date, end_date

    def display_summary(self, report_data):
        """Display report summary to console."""
        summary = report_data["summary"]

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("TEST FEE REPORT SUMMARY"))
        self.stdout.write("=" * 50)

        self.stdout.write(f"Period: {report_data['period']['start_date']} to {report_data['period']['end_date']}")
        self.stdout.write(f"Total Transactions: {summary['total_transactions']}")
        self.stdout.write(f"Paid Transactions: {summary['paid_transactions']}")
        self.stdout.write(f"Unpaid Transactions: {summary['unpaid_transactions']}")
        self.stdout.write(f"Total Fees Charged: ${summary['total_fees_charged']}")
        self.stdout.write(f"Total Fees Collected: ${summary['total_fees_collected']}")
        self.stdout.write(f"Total Outstanding: ${summary['total_outstanding']}")

        # Payment methods breakdown
        if report_data["payment_methods"]:
            self.stdout.write("\nPayment Methods:")
            for method, data in report_data["payment_methods"].items():
                self.stdout.write(f"  {method}: {data['count']} transactions, ${data['total_amount']}")

        self.stdout.write("=" * 50 + "\n")

    def export_reports(self, report_data, output_dir, options):
        """Export report data in requested formats."""
        period = report_data["period"]
        filename_base = f"test_fee_report_{period['start_date']}_{period['end_date']}"

        if options["format"] in ["json", "both"]:
            # Export JSON report
            json_file = output_dir / f"{filename_base}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, default=str)

            self.stdout.write(self.style.SUCCESS(f"JSON report exported: {json_file}"))

        if options["format"] in ["csv", "both"]:
            # Export CSV summary
            csv_file = output_dir / f"{filename_base}_summary.csv"
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Write headers
                writer.writerow(
                    [
                        "Test Number",
                        "Student Name",
                        "Amount",
                        "Payment Method",
                        "Is Paid",
                        "Paid Date",
                        "Finance Transaction ID",
                        "Created Date",
                    ],
                )

                # Write transaction data
                for txn in report_data["transactions"]:
                    writer.writerow(
                        [
                            txn["test_number"],
                            txn["student_name"],
                            txn["amount"],
                            txn["payment_method"],
                            "Yes" if txn["is_paid"] else "No",
                            (txn["paid_date"].strftime("%Y-%m-%d") if txn["paid_date"] else ""),
                            txn["finance_transaction_id"] or "",
                            txn["created_date"].strftime("%Y-%m-%d %H:%M:%S"),
                        ],
                    )

            self.stdout.write(self.style.SUCCESS(f"CSV report exported: {csv_file}"))

    def export_gl_entries(self, integrator, start_date, end_date, output_dir):
        """Export G/L entries for accounting software."""
        gl_entries = integrator.export_gl_entries(start_date, end_date)

        if not gl_entries:
            self.stdout.write(self.style.WARNING("No G/L entries to export for this period."))
            return

        filename = f"test_fee_gl_entries_{start_date}_{end_date}.csv"
        gl_file = output_dir / filename

        with open(gl_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Write headers
            writer.writerow(
                [
                    "Date",
                    "Account Code",
                    "Account Name",
                    "Debit Amount",
                    "Credit Amount",
                    "Description",
                    "Reference",
                ],
            )

            # Write G/L entries
            for entry in gl_entries:
                writer.writerow(
                    [
                        entry["date"].strftime("%Y-%m-%d"),
                        entry["account_code"],
                        entry["account_name"],
                        entry["debit_amount"],
                        entry["credit_amount"],
                        entry["description"],
                        entry["reference"],
                    ],
                )

        self.stdout.write(self.style.SUCCESS(f"G/L entries exported: {gl_file}"))

        # Display G/L summary
        self.stdout.write("\nG/L ENTRIES SUMMARY:")
        total_debits = sum(entry["debit_amount"] for entry in gl_entries)
        total_credits = sum(entry["credit_amount"] for entry in gl_entries)

        self.stdout.write(f"Total Debits: ${total_debits}")
        self.stdout.write(f"Total Credits: ${total_credits}")
        self.stdout.write(f"Difference: ${total_debits - total_credits}")

        if total_debits != total_credits:
            self.stdout.write(self.style.ERROR("WARNING: Debits and credits do not balance!"))
