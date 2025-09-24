"""Management command for NGO scholarship operations.

This command provides various operations for managing NGO-funded scholarships
efficiently, including bulk imports, transfers, and report generation.
"""

import csv
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.utils import timezone

from apps.scholarships.services import (
    NGOPortalService,
    NGOScholarshipTransferService,
)


class Command(BaseCommand):
    """Management command for NGO scholarship operations."""

    help = "Manage NGO-funded scholarships (import, transfer, report)"

    def add_arguments(self, parser):
        """Add command arguments."""
        subparsers = parser.add_subparsers(
            dest="subcommand", help="NGO scholarship operation to perform", required=True
        )

        import_parser = subparsers.add_parser("import", help="Bulk import sponsored students from CSV")
        import_parser.add_argument("sponsor_code", help="NGO sponsor code (e.g., CRST, PLF)")
        import_parser.add_argument("csv_file", help="Path to CSV file with student data")
        import_parser.add_argument("--dry-run", action="store_true", help="Validate without creating records")

        # Transfer dropped students
        transfer_parser = subparsers.add_parser(
            "transfer", help="Transfer financial responsibility for dropped students"
        )
        transfer_parser.add_argument("sponsor_code", help="NGO sponsor code")
        transfer_parser.add_argument("--student-id", help="Specific student ID to transfer (optional)")
        transfer_parser.add_argument(
            "--end-date",
            type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
            help="End date for sponsorship (YYYY-MM-DD)",
        )
        transfer_parser.add_argument("--reason", default="NGO sponsorship terminated", help="Reason for transfer")
        transfer_parser.add_argument("--all", action="store_true", help="Transfer all students from this NGO")

        # Generate reports
        report_parser = subparsers.add_parser("report", help="Generate NGO sponsor reports")
        report_parser.add_argument("sponsor_code", help="NGO sponsor code")
        report_parser.add_argument(
            "--type",
            choices=["dashboard", "financial", "grades", "attendance", "comprehensive"],
            default="dashboard",
            help="Type of report to generate",
        )
        report_parser.add_argument(
            "--start-date",
            type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
            help="Report start date (YYYY-MM-DD)",
        )
        report_parser.add_argument(
            "--end-date", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(), help="Report end date (YYYY-MM-DD)"
        )
        report_parser.add_argument("--output", help="Output file path (optional)")

        # List NGO students
        list_parser = subparsers.add_parser("list", help="List sponsored students for an NGO")
        list_parser.add_argument("sponsor_code", help="NGO sponsor code")
        list_parser.add_argument("--active-only", action="store_true", help="Show only active sponsorships")

    def handle(self, *args, **options):
        """Handle the command."""
        subcommand = options["subcommand"]

        if subcommand == "import":
            self.handle_import(options)
        elif subcommand == "transfer":
            self.handle_transfer(options)
        elif subcommand == "report":
            self.handle_report(options)
        elif subcommand == "list":
            self.handle_list(options)

    def handle_import(self, options):
        """Handle bulk import of sponsored students."""
        sponsor_code = options["sponsor_code"]
        csv_file = options["csv_file"]
        dry_run = options.get("dry_run", False)

        # Validate CSV file exists
        csv_path = Path(csv_file)
        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_file}")

        self.stdout.write(f"Importing sponsored students for {sponsor_code}...")

        # Load CSV data
        student_data = []
        with open(csv_path, encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Expected columns: student_id, type, start_date, notes
                student_data.append(
                    {
                        "student_id": row["student_id"],
                        "type": row.get("type", "FULL"),
                        "start_date": (
                            datetime.strptime(row["start_date"], "%Y-%m-%d").date()
                            if "start_date" in row
                            else timezone.now().date()
                        ),
                        "notes": row.get("notes", ""),
                    }
                )

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would import {len(student_data)} students"))
            for data in student_data[:5]:  # Show first 5
                self.stdout.write(f"  - Student {data['student_id']}")
            if len(student_data) > 5:
                self.stdout.write(f"  ... and {len(student_data) - 5} more")
            return

        # Perform import
        results = NGOPortalService.bulk_import_sponsored_students(sponsor_code, student_data)

        # Display results
        self.stdout.write(self.style.SUCCESS(f"Successfully imported {results['successful']} students"))

        if results["failed"] > 0:
            self.stdout.write(self.style.ERROR(f"Failed to import {results['failed']} students:"))
            for error in results["errors"]:
                self.stdout.write(f"  - Student {error['student_id']}: {error['error']}")

    def handle_transfer(self, options):
        """Handle transfer of dropped students."""
        sponsor_code = options["sponsor_code"]
        student_id = options.get("student_id")
        end_date = options.get("end_date")
        reason = options["reason"]
        transfer_all = options.get("all", False)

        if transfer_all:
            # Transfer all students from NGO
            self.stdout.write(f"Transferring all students from {sponsor_code}...")

            results = NGOScholarshipTransferService.bulk_transfer_ngo_students(sponsor_code, end_date, reason)

            # Display results
            successful = sum(1 for r in results if r.success)
            failed = sum(1 for r in results if not r.success)

            self.stdout.write(self.style.SUCCESS(f"Successfully transferred {successful} students"))

            if failed > 0:
                self.stdout.write(self.style.ERROR(f"Failed to transfer {failed} students"))

            # Show outstanding balances
            total_outstanding = sum(r.outstanding_balance for r in results if r.success)
            if total_outstanding > 0:
                self.stdout.write(f"Total outstanding balance transferred: ${total_outstanding}")

        elif student_id:
            # Transfer specific student
            from apps.scholarships.models import SponsoredStudent

            try:
                sponsored_student = SponsoredStudent.objects.get(
                    sponsor__code=sponsor_code, student__student_id=student_id, end_date__isnull=True
                )
            except SponsoredStudent.DoesNotExist as err:
                raise CommandError(
                    f"No active sponsorship found for student {student_id} with sponsor {sponsor_code}"
                ) from err

            self.stdout.write(f"Transferring student {student_id} from {sponsor_code}...")

            result = NGOScholarshipTransferService.transfer_scholarship_to_student(sponsored_student, end_date, reason)

            if result.success:
                self.stdout.write(self.style.SUCCESS("Transfer completed successfully"))
                if result.outstanding_balance > 0:
                    self.stdout.write(f"Outstanding balance: ${result.outstanding_balance}")
            else:
                self.stdout.write(self.style.ERROR(f"Transfer failed: {result.error_message}"))
        else:
            raise CommandError("Must specify either --student-id or --all for transfer")

    def handle_report(self, options):
        """Handle report generation."""
        sponsor_code = options["sponsor_code"]
        report_type = options["type"]
        start_date = options.get("start_date")
        end_date = options.get("end_date")
        output_file = options.get("output")

        self.stdout.write(f"Generating {report_type} report for {sponsor_code}...")

        if report_type == "dashboard":
            # Generate dashboard data
            data = NGOPortalService.get_ngo_dashboard_data(sponsor_code)

            if "error" in data:
                raise CommandError(data["error"])

            # Display dashboard summary
            self.stdout.write(f"\nNGO Dashboard: {data['sponsor']['name']}")
            self.stdout.write(f"{'=' * 50}")
            self.stdout.write(f"Active Students: {data['students']['active_count']}")
            self.stdout.write(f"Payment Mode: {data['sponsor']['payment_mode']}")
            self.stdout.write(f"Discount: {data['sponsor']['discount_percentage']}%")

            if data["financial_summary"]:
                self.stdout.write("\nFinancial Summary:")
                self.stdout.write(f"  YTD Paid: ${data['financial_summary']['total_paid_ytd']}")
                self.stdout.write(f"  Outstanding: ${data['financial_summary']['outstanding_balance']}")

        else:
            # Generate other report types
            if not start_date or not end_date:
                raise CommandError(f"Start and end dates required for {report_type} reports")

            report_data = NGOPortalService.generate_sponsor_report(sponsor_code, report_type, start_date, end_date)

            if "error" in report_data:
                raise CommandError(report_data["error"])

            self.stdout.write(self.style.SUCCESS("Report generated successfully"))

        # Save to file if requested
        if output_file:
            import json

            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(data if report_type == "dashboard" else report_data, f, indent=2, default=str)

            self.stdout.write(f"Report saved to: {output_file}")

    def handle_list(self, options):
        """Handle listing sponsored students."""
        sponsor_code = options["sponsor_code"]
        active_only = options.get("active_only", False)

        from apps.scholarships.models import Sponsor, SponsoredStudent

        try:
            sponsor = Sponsor.objects.get(code=sponsor_code)
        except Sponsor.DoesNotExist as err:
            raise CommandError(f"Sponsor {sponsor_code} not found") from err

        # Get sponsored students
        sponsorships = SponsoredStudent.objects.filter(sponsor=sponsor)

        if active_only:
            today = timezone.now().date()
            sponsorships = sponsorships.filter(start_date__lte=today).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
            )

        sponsorships = sponsorships.select_related("student__person").order_by("-start_date")

        # Display results
        self.stdout.write(f"\nSponsored Students for {sponsor.name}")
        self.stdout.write(f"{'=' * 70}")
        self.stdout.write(f"{'Student ID':<12} {'Name':<30} {'Type':<10} {'Status':<10}")
        self.stdout.write(f"{'-' * 70}")

        for sponsorship in sponsorships:
            status = "Active" if sponsorship.is_currently_active else "Ended"
            self.stdout.write(
                f"{sponsorship.student.student_id:<12} "
                f"{sponsorship.student.person.full_name:<30} "
                f"{sponsorship.sponsorship_type:<10} "
                f"{status:<10}"
            )

        self.stdout.write(f"\nTotal: {sponsorships.count()} students")
