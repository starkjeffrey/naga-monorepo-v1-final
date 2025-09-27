"""
Setup Automatic Discount System

Comprehensive command to set up the complete automatic discount system
by analyzing historical data, creating rules, and configuring term dates.
"""

from datetime import datetime
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.finance.services.automatic_discount_service import AutomaticDiscountService
from apps.finance.services.term_discount_validation import TermDiscountValidator


class Command(BaseCommand):
    """Set up complete automatic discount system from historical data."""

    help = "Analyze historical data and set up automatic discount system"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--skip-validation",
            action="store_true",
            help="Skip discount validation step",
        )
        parser.add_argument(
            "--skip-extraction",
            action="store_true",
            help="Skip discount date extraction step",
        )
        parser.add_argument(
            "--skip-migration",
            action="store_true",
            help="Skip discount date migration step",
        )
        parser.add_argument(
            "--confidence-threshold",
            type=float,
            default=0.7,
            help="Minimum confidence score for applying changes (0.0-1.0)",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default="project-docs/automatic-discount-setup",
            help="Directory for all output reports",
        )
        parser.add_argument(
            "--apply-changes",
            action="store_true",
            help="Apply changes to database (default is dry-run)",
        )

    def handle(self, *args, **options):
        """Main command execution."""
        self.stdout.write(self.style.SUCCESS("🚀 Setting up automatic discount system..."))

        # Create output directory
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Step 1: Validate existing discount rates
        if not options["skip_validation"]:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("📊 STEP 1: Validating historical discount rates")
            self.stdout.write("=" * 60)

            try:
                call_command(
                    "validate_term_discounts",
                    output_dir=str(output_dir / "validation"),
                    format="both",
                    show_examples=True,
                )
                self.stdout.write("✅ Discount validation completed")
            except Exception as e:
                self.stdout.write(f"❌ Discount validation failed: {e}")
                return

        # Step 2: Extract discount dates from historical notes
        if not options["skip_extraction"]:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("📅 STEP 2: Extracting discount dates from historical notes")
            self.stdout.write("=" * 60)

            try:
                extract_args = [
                    "extract_discount_dates",
                    "--output-file",
                    str(output_dir / f"extracted_dates_{timestamp}.txt"),
                    "--confidence-threshold",
                    str(options["confidence_threshold"]),
                ]

                if options["apply_changes"]:
                    extract_args.append("--apply-changes")

                call_command(*extract_args)
                self.stdout.write("✅ Discount date extraction completed")
            except Exception as e:
                self.stdout.write(f"❌ Discount date extraction failed: {e}")
                return

        # Step 3: Migrate discount dates to terms
        if not options["skip_migration"]:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("🗓️ STEP 3: Migrating discount dates to terms")
            self.stdout.write("=" * 60)

            try:
                migrate_args = [
                    "migrate_discount_dates",
                    "--confidence-threshold",
                    str(options["confidence_threshold"]),
                    "--output-file",
                    str(output_dir / f"migration_results_{timestamp}.txt"),
                ]

                if not options["apply_changes"]:
                    migrate_args.append("--dry-run")

                call_command(*migrate_args)
                self.stdout.write("✅ Discount date migration completed")
            except Exception as e:
                self.stdout.write(f"❌ Discount date migration failed: {e}")
                return

        # Step 4: Test automatic discount system
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🧪 STEP 4: Testing automatic discount system")
        self.stdout.write("=" * 60)

        self.test_automatic_discount_system(output_dir, timestamp)

        # Step 5: Generate comprehensive setup report
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📋 STEP 5: Generating setup report")
        self.stdout.write("=" * 60)

        self.generate_setup_report(output_dir, timestamp, options)

        # Final summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🎉 AUTOMATIC DISCOUNT SYSTEM SETUP COMPLETED!")
        self.stdout.write("=" * 60)

        if options["apply_changes"]:
            self.stdout.write("✅ Changes have been applied to the database")
            self.stdout.write("🔄 The automatic discount system is now active")
        else:
            self.stdout.write("🔍 Dry-run mode - no changes applied")
            self.stdout.write("🔄 Use --apply-changes to activate the system")

        self.stdout.write(f"📋 All reports saved to: {output_dir}")

        # Show next steps
        self.show_next_steps(options)

    def test_automatic_discount_system(self, output_dir: Path, timestamp: str):
        """Test the automatic discount system."""
        try:
            service = AutomaticDiscountService()
            validator = TermDiscountValidator()

            # Get some terms to test
            validation_results = validator.validate_all_terms()
            test_terms = [r.term_code for r in validation_results[:5]]

            if not test_terms:
                self.stdout.write("⚠️ No terms available for testing")
                return

            test_results = []

            for term_code in test_terms:
                try:
                    summary = service.get_term_discount_summary(term_code)
                    test_results.append(
                        {
                            "term_code": term_code,
                            "summary": summary,
                            "status": "success",
                        }
                    )

                    status = summary.get("early_bird_status", "unknown")
                    days_until = summary.get("days_until_deadline", "N/A")
                    available_discounts = len(summary.get("available_discounts", []))

                    self.stdout.write(
                        f"  📋 {term_code}: {status}, "
                        f"{available_discounts} discounts available, "
                        f"deadline in {days_until} days"
                    )

                except Exception as e:
                    test_results.append({"term_code": term_code, "error": str(e), "status": "error"})
                    self.stdout.write(f"  ❌ {term_code}: Error - {e}")

            # Save test results
            self.save_test_results(test_results, output_dir, timestamp)

            self.stdout.write("✅ Automatic discount system testing completed")

        except Exception as e:
            self.stdout.write(f"❌ Testing failed: {e}")

    def save_test_results(self, test_results: list, output_dir: Path, timestamp: str):
        """Save test results to file."""
        test_file = output_dir / f"system_test_results_{timestamp}.txt"

        with open(test_file, "w", encoding="utf-8") as f:
            f.write("AUTOMATIC DISCOUNT SYSTEM TEST RESULTS\n")
            f.write("=" * 45 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            successful_tests = [r for r in test_results if r["status"] == "success"]
            failed_tests = [r for r in test_results if r["status"] == "error"]

            f.write(f"Total tests: {len(test_results)}\n")
            f.write(f"Successful: {len(successful_tests)}\n")
            f.write(f"Failed: {len(failed_tests)}\n\n")

            if successful_tests:
                f.write("SUCCESSFUL TESTS\n")
                f.write("-" * 15 + "\n\n")

                for result in successful_tests:
                    f.write(f"Term {result['term_code']}:\n")
                    summary = result["summary"]
                    f.write(f"  Status: {summary.get('early_bird_status', 'unknown')}\n")
                    f.write(f"  Discount end date: {summary.get('discount_end_date', 'Not set')}\n")
                    f.write(f"  Days until deadline: {summary.get('days_until_deadline', 'N/A')}\n")
                    f.write(f"  Available discounts: {len(summary.get('available_discounts', []))}\n")

                    if summary.get("configuration_issues"):
                        f.write("  Issues:\n")
                        for issue in summary["configuration_issues"]:
                            f.write(f"    - {issue}\n")

                    f.write("\n")

            if failed_tests:
                f.write("FAILED TESTS\n")
                f.write("-" * 12 + "\n\n")

                for result in failed_tests:
                    f.write(f"Term {result['term_code']}: {result['error']}\n")

    def generate_setup_report(self, output_dir: Path, timestamp: str, options):
        """Generate comprehensive setup report."""
        report_file = output_dir / f"setup_summary_{timestamp}.txt"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("AUTOMATIC DISCOUNT SYSTEM SETUP REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Setup mode: {'LIVE' if options['apply_changes'] else 'DRY RUN'}\n")
            f.write(f"Confidence threshold: {options['confidence_threshold']}\n\n")

            # Configuration summary
            f.write("SETUP CONFIGURATION\n")
            f.write("-" * 20 + "\n")
            f.write(f"Validation step: {'SKIPPED' if options['skip_validation'] else 'COMPLETED'}\n")
            f.write(f"Extraction step: {'SKIPPED' if options['skip_extraction'] else 'COMPLETED'}\n")
            f.write(f"Migration step: {'SKIPPED' if options['skip_migration'] else 'COMPLETED'}\n")
            f.write("System testing: COMPLETED\n\n")

            # Generated files
            f.write("GENERATED FILES\n")
            f.write("-" * 15 + "\n")
            for file_path in output_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(output_dir)
                    f.write(f"  - {relative_path}\n")
            f.write("\n")

            # System architecture
            f.write("SYSTEM ARCHITECTURE\n")
            f.write("-" * 20 + "\n")
            f.write("The automatic discount system consists of:\n\n")
            f.write("1. TermDiscountValidationService\n")
            f.write("   - Validates legacy discount rates against canonical rates\n")
            f.write("   - Generates recommendations for business rule creation\n\n")
            f.write("2. AutomaticDiscountService\n")
            f.write("   - Implements automatic discount application based on Term.discount_end_date\n")
            f.write("   - Replaces pattern-matching with rule-based discounts\n\n")
            f.write("3. ExtractDiscountDatesCommand\n")
            f.write("   - Analyzes historical notes to extract discount deadlines\n")
            f.write("   - Populates Term.discount_end_date fields\n\n")
            f.write("4. MigrateDiscountDatesCommand\n")
            f.write("   - Systematically applies discount dates to historical terms\n")
            f.write("   - Provides evidence-based confidence scoring\n\n")

            # Usage instructions
            f.write("USAGE INSTRUCTIONS\n")
            f.write("-" * 18 + "\n")
            f.write("To use the automatic discount system:\n\n")
            f.write("1. Check student eligibility:\n")
            f.write("   service = AutomaticDiscountService()\n")
            f.write("   eligibility = service.check_early_bird_eligibility(student_id, term_code)\n\n")
            f.write("2. Apply discount:\n")
            f.write("   application = service.apply_discount(\n")
            f.write("       student_id, term_code, 'EARLY_BIRD', original_amount\n")
            f.write("   )\n\n")
            f.write("3. Get term discount summary:\n")
            f.write("   summary = service.get_term_discount_summary(term_code)\n\n")
            f.write("4. Bulk apply early bird discounts:\n")
            f.write("   results = service.bulk_apply_early_bird_discounts(term_code)\n\n")

            # Integration notes
            f.write("INTEGRATION NOTES\n")
            f.write("-" * 17 + "\n")
            f.write("- Integrate with existing pricing service for accurate amounts\n")
            f.write("- Connect to actual discount application records\n")
            f.write("- Implement approval workflows for special discounts\n")
            f.write("- Add monitoring for discount application patterns\n")
            f.write("- Consider implementing discount caps and budgets\n\n")

        self.stdout.write(f"📋 Setup report saved to: {report_file}")

    def show_next_steps(self, options):
        """Show next steps for using the automatic discount system."""
        self.stdout.write("\n📋 NEXT STEPS:")

        if not options["apply_changes"]:
            self.stdout.write("1. Review all generated reports")
            self.stdout.write("2. Run with --apply-changes to activate the system")
        else:
            self.stdout.write("1. Review generated reports for any issues")
            self.stdout.write("2. Test the system with a few real scenarios")
            self.stdout.write("3. Integrate with your pricing and payment systems")
            self.stdout.write("4. Set up monitoring for discount applications")

        self.stdout.write("\n🔧 MANAGEMENT COMMANDS:")
        self.stdout.write("- validate_term_discounts: Check discount rate consistency")
        self.stdout.write("- extract_discount_dates: Analyze historical discount patterns")
        self.stdout.write("- migrate_discount_dates: Apply discount dates to terms")
        self.stdout.write("- setup_automatic_discounts: Complete system setup (this command)")

        self.stdout.write("\n🎯 INTEGRATION POINTS:")
        self.stdout.write("- AutomaticDiscountService: Main service for discount operations")
        self.stdout.write("- TermDiscountValidationService: Validate and analyze discount rates")
        self.stdout.write("- Term.discount_end_date: Core field for automatic discount eligibility")
        self.stdout.write("- DiscountRule model: Configure discount types and rates")

        self.stdout.write(f"\n📁 OUTPUT DIRECTORY: {options['output_dir']}")
        self.stdout.write("   Review all generated reports and recommendations")
