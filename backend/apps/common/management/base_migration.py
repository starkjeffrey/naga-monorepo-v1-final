"""Base migration command class with mandatory comprehensive audit reporting.

This class ensures ALL migration scripts produce detailed audit reports for
accountability, traceability, and data integrity verification.

ARCHITECTURAL REQUIREMENT: Every migration script MUST inherit from this class
and implement audit reporting. No exceptions.
"""

import json
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand


class BaseMigrationCommand(BaseCommand, ABC):
    """Base class for all migration commands with mandatory audit reporting.

    Features:
    - Comprehensive audit report generation
    - Error categorization and tracking
    - Performance metrics collection
    - Data integrity validation
    - Standardized report format
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.migration_start_time = None
        self.audit_data = {
            "migration_info": {},
            "summary": {
                "input": {},
                "output": {},
                "rejected": {"total_rejected": 0, "rejection_breakdown": {}},
            },
            "detailed_rejections": {},
            "performance_metrics": {},
            "data_integrity": {},
            "samples": {},
        }
        self.rejection_categories = []
        self.detailed_rejections = {}

    def handle(self, *args, **options):
        """Main entry point with audit reporting wrapper."""
        self.migration_start_time = time.time()
        script_name = self.__class__.__module__.split(".")[-1]

        self.audit_data["migration_info"] = {
            "script": f"{script_name}.py",
            "timestamp": datetime.now(UTC).isoformat(),
            "mode": "migration",
            "command_options": {k: v for k, v in options.items() if k not in ["verbosity", "settings", "pythonpath"]},
        }

        try:
            # Initialize rejection categories
            self.rejection_categories = self.get_rejection_categories()
            for category in self.rejection_categories:
                self.detailed_rejections[category] = []
                self.audit_data["summary"]["rejected"]["rejection_breakdown"][category] = 0

            # Execute the migration
            result = self.execute_migration(*args, **options)

            # Finalize audit data
            self._finalize_audit_data()

            # Generate and save audit report
            self._generate_audit_report()
        except Exception as e:
            # Ensure audit report is generated even on failure
            self.audit_data["migration_info"]["error"] = str(e)
            self.audit_data["migration_info"]["status"] = "failed"
            self._finalize_audit_data()
            self._generate_audit_report()
            raise
        else:
            return result

    @abstractmethod
    def execute_migration(self, *args, **options) -> Any:
        """Execute the actual migration logic.

        Subclasses must implement this method and use the provided
        audit tracking methods to record progress and errors.
        """

    @abstractmethod
    def get_rejection_categories(self) -> list[str]:
        """Return list of possible rejection categories for this migration.

        Example: ["missing_critical_data", "duplicate_constraint",
                 "data_validation_error", "database_error"]
        """

    def record_success(self, record_type: str, count: int = 1):
        """Record successful operations by type."""
        if record_type not in self.audit_data["summary"]["output"]:
            self.audit_data["summary"]["output"][record_type] = 0
        self.audit_data["summary"]["output"][record_type] += count

    def record_rejection(
        self,
        category: str,
        record_id: str,
        reason: str,
        error_details: str | None = None,
        raw_data: dict | None = None,
    ):
        """Record a rejected record with full details."""
        if category not in self.rejection_categories:
            msg = f"Invalid rejection category: {category}"
            raise ValueError(msg)

        rejection_record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "reason": category,
            "record_id": record_id,
            "reason_details": reason,
        }

        if error_details:
            rejection_record["error_details"] = error_details
        if raw_data:
            rejection_record["raw_data"] = raw_data

        self.detailed_rejections[category].append(rejection_record)
        self.audit_data["summary"]["rejected"]["rejection_breakdown"][category] += 1
        self.audit_data["summary"]["rejected"]["total_rejected"] += 1

    def record_input_stats(self, **stats):
        """Record input statistics."""
        self.audit_data["summary"]["input"].update(stats)

    def record_performance_metric(self, metric_name: str, value: Any):
        """Record performance metrics."""
        self.audit_data["performance_metrics"][metric_name] = value

    def record_data_integrity(self, check_name: str, result: Any):
        """Record data integrity validation results."""
        self.audit_data["data_integrity"][check_name] = result

    def record_sample_data(self, sample_type: str, samples: list[dict]):
        """Record sample data for verification."""
        self.audit_data["samples"][sample_type] = samples

    def _finalize_audit_data(self):
        """Finalize audit data with calculated metrics."""
        duration = time.time() - self.migration_start_time
        self.audit_data["migration_info"]["duration_seconds"] = duration
        self.audit_data["migration_info"]["status"] = "completed"

        # Copy detailed rejections to audit data
        self.audit_data["detailed_rejections"] = self.detailed_rejections

        # Calculate success rate
        total_processed = sum(v for v in self.audit_data["summary"]["output"].values() if isinstance(v, int | float))
        self.audit_data["summary"]["rejected"]["total_rejected"]

        # Get numeric input values only for calculation
        input_values = [v for v in self.audit_data["summary"]["input"].values() if isinstance(v, int | float)]
        total_input = sum(input_values) if input_values else 0

        if total_input > 0:
            self.audit_data["summary"]["success_rate"] = (total_processed / total_input) * 100

    def _generate_audit_report(self):
        """Generate and save comprehensive audit report."""
        # Ensure reports directory exists
        reports_dir = Path("project-docs/migration-reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        script_name = str(self.audit_data["migration_info"]["script"]).replace(".py", "")
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{script_name}_migration_report_{timestamp}.json"
        filepath = reports_dir / filename

        # Write audit report
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(self.audit_data, f, indent=2, ensure_ascii=False, default=str)

        # Print summary
        self.stdout.write(self.style.SUCCESS(f"\n📋 MIGRATION AUDIT REPORT GENERATED: {filepath}"))
        self._print_audit_summary()

    def _print_audit_summary(self):
        """Print migration summary to console."""
        summary = self.audit_data["summary"]

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 MIGRATION SUMMARY"))
        self.stdout.write("=" * 60)

        # Input stats
        if summary["input"]:
            self.stdout.write("📥 INPUT:")
            for key, value in summary["input"].items():
                if isinstance(value, int | float):
                    self.stdout.write(f"   {key}: {value:,}")
                else:
                    self.stdout.write(f"   {key}: {value}")

        # Output stats
        if summary["output"]:
            self.stdout.write("\n✅ SUCCESSFUL OPERATIONS:")
            for key, value in summary["output"].items():
                self.stdout.write(f"   {key}: {value:,}")

        # Rejection stats
        if summary["rejected"]["total_rejected"] > 0:
            self.stdout.write(f"\n❌ REJECTIONS: {summary['rejected']['total_rejected']:,}")
            for category, count in dict(summary["rejected"]["rejection_breakdown"]).items():
                if count > 0:
                    self.stdout.write(f"   {category}: {count:,}")

        # Performance
        duration = self.audit_data["migration_info"]["duration_seconds"]
        self.stdout.write(f"\n⏱️  DURATION: {duration:.2f} seconds")

        if "success_rate" in summary:
            self.stdout.write(f"📈 SUCCESS RATE: {summary['success_rate']:.2f}%")

        self.stdout.write("=" * 60)
