"""Management command to generate QuickBooks-friendly financial reports.

Generates simple reports that the school accountant can easily copy
into QuickBooks. Focuses on monthly cash receipts summaries.

Usage:
    # Generate for specific month
    python manage.py generate_quickbooks_reports --year 2025 --month 1

    # Generate for previous month (default)
    python manage.py generate_quickbooks_reports

    # Generate journal entry format
    python manage.py generate_quickbooks_reports --journal

    # Generate daily deposits report
    python manage.py generate_quickbooks_reports --deposits

    # Save to file
    python manage.py generate_quickbooks_reports --output report.txt

    # Export as CSV
    python manage.py generate_quickbooks_reports --format csv --output report.csv
"""

import logging
import os
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.finance.services import QuickBooksReportService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate QuickBooks-friendly financial reports for manual entry"

    def add_arguments(self, parser):
        """Add command arguments."""
        # Date parameters
        parser.add_argument(
            "--year",
            type=int,
            help="Year to report (default: previous month)",
        )
        parser.add_argument(
            "--month",
            type=int,
            help="Month to report 1-12 (default: previous month)",
        )

        # Report types
        parser.add_argument(
            "--summary",
            action="store_true",
            default=True,
            help="Generate cash receipts summary (default)",
        )
        parser.add_argument(
            "--journal",
            action="store_true",
            help="Generate journal entry format",
        )
        parser.add_argument(
            "--deposits",
            action="store_true",
            help="Generate daily deposits report",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Generate all report types",
        )

        # Output options
        parser.add_argument(
            "--format",
            type=str,
            choices=["readable", "csv"],
            default="readable",
            help="Output format (default: readable)",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Save output to file instead of stdout",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        try:
            # Determine period to report
            year, month = self._get_reporting_period(options)

            self.stdout.write(
                self.style.SUCCESS(f"\nGenerating QuickBooks reports for {self._get_month_name(month)} {year}"),
            )

            # Initialize service
            service = QuickBooksReportService()

            # Collect output
            output_lines = []

            # Generate requested reports
            if options["all"] or options["journal"]:
                output_lines.append("=" * 80)
                output_lines.append("QUICKBOOKS JOURNAL ENTRY")
                output_lines.append("=" * 80)
                output_lines.append("")
                output_lines.append(service.generate_quickbooks_journal_entry(year, month))
                output_lines.append("")
                output_lines.append("")

            if options["all"] or options["deposits"]:
                output_lines.append("=" * 80)
                output_lines.append("DAILY DEPOSITS REPORT")
                output_lines.append("=" * 80)
                output_lines.append("")
                deposits_report = service.generate_bank_deposit_report(year, month)
                if options["format"] == "readable":
                    output_lines.append(deposits_report)
                else:
                    output_lines.append(deposits_report)
                output_lines.append("")
                output_lines.append("")

            # Default: Cash receipts summary
            if not (options["journal"] or options["deposits"]) or options["all"]:
                summary_report = service.generate_monthly_cash_receipts_summary(year, month, format=options["format"])
                if options["format"] == "readable":
                    output_lines.append(summary_report)
                else:
                    output_lines.append(summary_report)

            # Output results
            full_output = "\n".join(str(line) for line in output_lines)

            if options.get("output"):
                # Save to file
                self._save_to_file(full_output, options["output"])
                self.stdout.write(self.style.SUCCESS(f"Report saved to: {options['output']}"))
            else:
                # Print to stdout
                self.stdout.write(full_output)

            # Show helpful tips
            self.stdout.write("\n")
            self.stdout.write(self.style.SUCCESS("✓ Report generated successfully!"))
            self.stdout.write("\nTip: This report is designed to be easily copied into QuickBooks.")
            self.stdout.write("     The journal entry format can be entered directly as a journal entry.")
            self.stdout.write("     The daily deposits should match your bank deposits for reconciliation.")

        except Exception as e:
            logger.exception("Error generating QuickBooks reports")
            msg = f"Failed to generate reports: {e}"
            raise CommandError(msg) from e

    def _get_reporting_period(self, options):
        """Determine which period to report."""
        if options.get("year") and options.get("month"):
            # Explicit period specified
            year = options["year"]
            month = options["month"]

            if month < 1 or month > 12:
                msg = "Month must be between 1 and 12"
                raise CommandError(msg)

            # Don't report future periods
            today = timezone.now().date()
            if year > today.year or (year == today.year and month > today.month):
                msg = "Cannot report future periods"
                raise CommandError(msg)

        else:
            # Default to previous month
            today = timezone.now().date()
            first_of_month = today.replace(day=1)
            last_month = first_of_month - timedelta(days=1)
            year = last_month.year
            month = last_month.month

        return year, month

    def _get_month_name(self, month: int) -> str:
        """Get month name."""
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        return months[month - 1]

    def _save_to_file(self, content: str, filename: str):
        """Save content to file."""
        # Ensure directory exists
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        # Make file readable by accounting staff
        os.chmod(filename, 0o644)
