"""
Django management command for validating term discount rates.

This command validates legacy discount rates against canonical rates
and generates comprehensive reports for business rule configuration.
"""

import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.finance.services.term_discount_validation import TermDiscountValidator


class Command(BaseCommand):
    """Validate discount rates across all terms with legacy data."""

    help = "Validate legacy discount rates against canonical rates and generate recommendations"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("--term", type=str, help="Validate specific term only (e.g., 240109E)")
        parser.add_argument(
            "--output-dir",
            type=str,
            default="project-docs/discount-validation-reports",
            help="Directory for validation reports",
        )
        parser.add_argument(
            "--format",
            choices=["json", "csv", "both"],
            default="both",
            help="Output format for reports",
        )
        parser.add_argument(
            "--show-examples",
            action="store_true",
            help="Include example records in output",
        )

    def handle(self, *args, **options):
        """Main command execution."""
        self.stdout.write("🔍 Starting term discount validation...")

        # Initialize validator
        validator = TermDiscountValidator()

        # Run validation
        if options["term"]:
            self.stdout.write(f"📊 Validating term: {options['term']}")
            results = validator.validate_term_discounts(options["term"])
            term_summary = validator.get_term_summary(options["term"])
        else:
            self.stdout.write("📊 Validating all terms with legacy data...")
            results = validator.validate_all_terms()
            term_summary = None

        if not results:
            self.stdout.write(self.style.WARNING("⚠️ No discount data found for validation"))
            return

        # Generate reports
        self.generate_reports(validator, options, term_summary)

        # Show summary
        self.show_validation_summary(results)

        self.stdout.write(self.style.SUCCESS("✅ Term discount validation completed!"))

    def generate_reports(self, validator, options, term_summary=None):
        """Generate validation reports."""
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate comprehensive report
        comprehensive_report = validator.generate_comprehensive_report()

        if options["format"] in ["json", "both"]:
            self.generate_json_report(comprehensive_report, output_dir, timestamp, options)

        if options["format"] in ["csv", "both"]:
            self.generate_csv_reports(comprehensive_report, output_dir, timestamp)

        # Generate term-specific report if requested
        if term_summary:
            self.generate_term_report(term_summary, output_dir, timestamp)

        # Generate recommendations file
        self.generate_recommendations_file(comprehensive_report, output_dir, timestamp)

        self.stdout.write(f"📋 Reports generated in: {output_dir}")

    def generate_json_report(self, report, output_dir, timestamp, options):
        """Generate JSON format report."""
        # Remove examples if not requested to reduce file size
        if not options["show_examples"]:
            for result in report["validation_results"]:
                result.pop("examples", None)

        json_file = output_dir / f"discount_validation_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        self.stdout.write(f"  📄 JSON report: {json_file.name}")

    def generate_csv_reports(self, report, output_dir, timestamp):
        """Generate CSV format reports."""
        import csv

        # Main validation results CSV
        csv_file = output_dir / f"validation_results_{timestamp}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "term_code",
                "discount_type",
                "legacy_rate",
                "canonical_rate",
                "status",
                "variance",
                "variance_percentage",
                "sample_count",
                "confidence_score",
                "notes",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in report["validation_results"]:
                # Remove non-CSV friendly fields
                csv_result = {k: v for k, v in result.items() if k in fieldnames}
                writer.writerow(csv_result)

        self.stdout.write(f"  📄 CSV results: {csv_file.name}")

        # Recommendations CSV
        rec_file = output_dir / f"recommendations_{timestamp}.csv"
        with open(rec_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["term_code", "discount_type", "recommendation"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in report["validation_results"]:
                term_code = result["term_code"]
                discount_type = result["discount_type"]
                for rec in result["recommendations"]:
                    writer.writerow(
                        {
                            "term_code": term_code,
                            "discount_type": discount_type,
                            "recommendation": rec,
                        }
                    )

        self.stdout.write(f"  📄 CSV recommendations: {rec_file.name}")

    def generate_term_report(self, term_summary, output_dir, timestamp):
        """Generate term-specific report."""
        term_code = term_summary["term_code"]
        term_file = output_dir / f"term_{term_code}_{timestamp}.json"

        with open(term_file, "w", encoding="utf-8") as f:
            json.dump(term_summary, f, indent=2, default=str)

        self.stdout.write(f"  📄 Term report: {term_file.name}")

    def generate_recommendations_file(self, report, output_dir, timestamp):
        """Generate human-readable recommendations file."""
        rec_file = output_dir / f"recommendations_summary_{timestamp}.txt"

        with open(rec_file, "w", encoding="utf-8") as f:
            f.write("TERM DISCOUNT VALIDATION RECOMMENDATIONS\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Summary statistics
            summary = report["validation_summary"]
            f.write("VALIDATION SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"Terms analyzed: {summary['total_terms_analyzed']}\n")
            f.write(f"Discount validations: {summary['total_validation_results']}\n\n")

            # Status breakdown
            f.write("STATUS BREAKDOWN\n")
            f.write("-" * 20 + "\n")
            for status, count in summary["status_breakdown"].items():
                f.write(f"{status.upper()}: {count}\n")
            f.write("\n")

            # Confidence metrics
            if summary["confidence_metrics"]:
                f.write("CONFIDENCE METRICS\n")
                f.write("-" * 20 + "\n")
                metrics = summary["confidence_metrics"]
                f.write(f"Average confidence: {metrics['average_confidence']:.2f}\n")
                f.write(f"Min confidence: {metrics['min_confidence']:.2f}\n")
                f.write(f"Max confidence: {metrics['max_confidence']:.2f}\n\n")

            # Global recommendations
            f.write("PRIORITY RECOMMENDATIONS\n")
            f.write("-" * 25 + "\n")
            for i, rec in enumerate(report["recommendations"], 1):
                f.write(f"{i}. {rec}\n")
            f.write("\n")

            # Term-by-term issues
            f.write("TERM-SPECIFIC ISSUES\n")
            f.write("-" * 20 + "\n")

            # Group validation results by term
            term_results = {}
            for result in report["validation_results"]:
                term = result["term_code"]
                if term not in term_results:
                    term_results[term] = []
                term_results[term].append(result)

            for term_code, results in sorted(term_results.items()):
                f.write(f"\nTerm {term_code}:\n")

                for result in results:
                    status_icon = {
                        "valid": "✅",
                        "invalid": "❌",
                        "missing_canonical": "🔶",
                        "suspicious": "⚠️",
                        "requires_review": "🔍",
                    }.get(result["status"], "❓")

                    f.write(f"  {status_icon} {result['discount_type']}: ")
                    f.write(f"{result['legacy_rate']}%")

                    if result["canonical_rate"]:
                        f.write(f" (canonical: {result['canonical_rate']}%)")

                    if result["variance_percentage"]:
                        f.write(f" [variance: {result['variance_percentage']:.1f}%]")

                    f.write(f" ({result['sample_count']} samples)\n")

                    # Show top recommendation for this result
                    if result["recommendations"]:
                        f.write(f"    → {result['recommendations'][0]}\n")

        self.stdout.write(f"  📄 Summary: {rec_file.name}")

    def show_validation_summary(self, results):
        """Show validation summary in console."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 VALIDATION SUMMARY")
        self.stdout.write("=" * 60)

        # Count by status
        status_counts = {}
        confidence_scores = []

        for result in results:
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            confidence_scores.append(result.confidence_score)

        # Show status breakdown
        self.stdout.write(f"Total validations: {len(results)}")
        for status, count in sorted(status_counts.items()):
            icon = {
                "valid": "✅",
                "invalid": "❌",
                "missing_canonical": "🔶",
                "suspicious": "⚠️",
                "requires_review": "🔍",
            }.get(status, "❓")
            self.stdout.write(f"{icon} {status.upper()}: {count}")

        # Show confidence metrics
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            self.stdout.write(f"Average confidence: {avg_confidence:.2f}")

        self.stdout.write("")

        # Show critical issues
        critical_issues = [r for r in results if r.status.value in ["invalid", "suspicious"]]

        if critical_issues:
            self.stdout.write("🚨 CRITICAL ISSUES REQUIRING ATTENTION:")
            for issue in critical_issues[:5]:  # Show top 5
                self.stdout.write(
                    f"  • {issue.term_code} {issue.discount_type}: "
                    f"{issue.legacy_rate}% (variance: {issue.variance_percentage:.1f}%)"
                )
            if len(critical_issues) > 5:
                self.stdout.write(f"  ... and {len(critical_issues) - 5} more")

        # Show missing canonical rates
        missing_canonical = [r for r in results if r.status.value == "missing_canonical"]

        if missing_canonical:
            self.stdout.write("")
            self.stdout.write("🔶 MISSING CANONICAL RATES:")
            discount_types = {r.discount_type for r in missing_canonical}
            for dtype in sorted(discount_types):
                avg_rate = sum(r.legacy_rate for r in missing_canonical if r.discount_type == dtype) / len(
                    [r for r in missing_canonical if r.discount_type == dtype]
                )

                self.stdout.write(f"  • {dtype}: suggested rate {avg_rate:.1f}%")
