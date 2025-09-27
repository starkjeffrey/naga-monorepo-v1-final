"""
Business Rules Validation Report

Management command to generate comprehensive business rules validation reports
for pipeline data quality assurance.
"""

from typing import Any, NotRequired, TypedDict, cast

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.data_pipeline.core.registry import get_registry


class CheckResult(TypedDict, total=False):
    total: int
    passed: int
    failed: int
    description: str
    details: NotRequired[dict[str, Any]]


class CriticalFailure(TypedDict):
    check: str
    success_rate: float
    failed_count: int


class ValidationResults(TypedDict):
    table_name: str
    stage_table: str
    total_records: int
    validation_checks: dict[str, CheckResult]
    overall_success_rate: float
    critical_failures: list[CriticalFailure]
    warnings: list[str]


class Command(BaseCommand):
    help = "Generate business rules validation reports for pipeline data"

    def add_arguments(self, parser):
        parser.add_argument(
            "table_name", type=str, help="Table to validate (e.g., students, academicclasses, or 'all')"
        )
        parser.add_argument(
            "--stage", type=int, choices=[3, 4, 5], default=4, help="Pipeline stage to validate (default: 4)"
        )
        parser.add_argument("--detailed", action="store_true", help="Show detailed validation errors and examples")
        parser.add_argument("--export-failures", type=str, help="Export validation failures to CSV file")
        parser.add_argument(
            "--threshold", type=float, default=95.0, help="Success rate threshold for warnings (default: 95.0%)"
        )

    def handle(self, *args, **options):
        """Main command handler"""
        table_name = options["table_name"]

        try:
            if table_name == "all":
                self._validate_all_tables(options)
            else:
                self._validate_single_table(table_name, options)

        except Exception as e:
            raise CommandError(f"Business rules validation failed: {e}") from e

    def _validate_all_tables(self, options: dict):
        """Validate business rules for all pipeline tables"""
        registry = get_registry()
        all_tables = registry.list_tables()

        self.stdout.write("🏢 Business Rules Validation Report - All Tables")
        self.stdout.write(f"{'=' * 80}")

        overall_results = []

        for table in all_tables:
            self.stdout.write(f"\n📋 Validating table: {table}")
            self.stdout.write(f"{'-' * 50}")

            result = self._validate_single_table(table, options, summary_only=True)
            overall_results.append((table, result))

        # Show overall summary
        self._show_overall_summary(cast("list[tuple[str, dict[str, Any]]]", overall_results), options)

    def _validate_single_table(
        self, table_name: str, options: dict, summary_only: bool = False
    ) -> dict[str, Any] | ValidationResults:
        """Validate business rules for a single table"""
        registry = get_registry()

        try:
            registry.get_config(table_name)
        except ValueError:
            raise CommandError(f"Table '{table_name}' not found in pipeline registry") from None

        if not summary_only:
            self.stdout.write(f"🔍 Business Rules Validation Report: {table_name}")
            self.stdout.write(f"{'=' * 80}")

        stage = options["stage"]
        stage_table = self._get_stage_table(table_name, stage)

        if not self._table_exists(stage_table):
            error_msg = f"Stage {stage} table not found: {stage_table}"
            if summary_only:
                return {"error": error_msg, "success_rate": 0.0}
            else:
                raise CommandError(error_msg)

        # Run validation checks
        validation_results = self._run_validation_checks(table_name, stage_table, options)

        if not summary_only:
            self._show_detailed_results(table_name, validation_results, options)

        return validation_results

    def _get_stage_table(self, table_name: str, stage: int) -> str:
        """Get the table name for the specified stage"""
        stage_mapping = {
            3: f"{table_name}_stage3_cleaned",
            4: f"{table_name}_stage4_valid",
            5: f"{table_name}_stage5_transformed",
        }
        return stage_mapping[stage]

    def _table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
            """,
                [table_name],
            )
            return cursor.fetchone()[0]

    def _run_validation_checks(self, table_name: str, stage_table: str, options: dict) -> ValidationResults:
        """Run all business rule validation checks"""
        results: ValidationResults = {
            "table_name": table_name,
            "stage_table": stage_table,
            "total_records": 0,
            "validation_checks": {},
            "overall_success_rate": 0.0,
            "critical_failures": [],
            "warnings": [],
        }

        with connection.cursor() as cursor:
            # Get total record count
            cursor.execute(f"SELECT COUNT(*) FROM {stage_table}")
            results["total_records"] = cursor.fetchone()[0]

            if results["total_records"] == 0:
                results["warnings"].append("No records found in stage table")
                return results

            # Run table-specific validation checks
            if table_name == "students":
                self._validate_students_business_rules(cursor, stage_table, results)
            elif table_name == "academicclasses":
                self._validate_academicclasses_business_rules(cursor, stage_table, results)
            elif table_name == "academiccoursetakers":
                self._validate_academiccoursetakers_business_rules(cursor, stage_table, results)
            elif table_name == "terms":
                self._validate_terms_business_rules(cursor, stage_table, results)
            elif table_name in ["receipt_headers", "receipt_items"]:
                self._validate_financial_business_rules(cursor, stage_table, results, table_name)
            else:
                self._validate_generic_business_rules(cursor, stage_table, results)

            # Calculate overall success rate
            total_checks = sum(check["total"] for check in results["validation_checks"].values())
            total_passed = sum(check["passed"] for check in results["validation_checks"].values())

            if total_checks > 0:
                results["overall_success_rate"] = (total_passed / total_checks) * 100

            # Identify critical failures
            threshold = options["threshold"]
            for check_name, check_result in results["validation_checks"].items():
                success_rate = (
                    (check_result["passed"] / check_result["total"]) * 100 if check_result["total"] > 0 else 100
                )
                if success_rate < threshold:
                    results["critical_failures"].append(
                        {"check": check_name, "success_rate": success_rate, "failed_count": check_result["failed"]}
                    )

        return results

    def _validate_students_business_rules(self, cursor, stage_table: str, results: ValidationResults) -> None:
        """Validate students table business rules"""
        checks: dict[str, CheckResult] = {}

        # Rule 1: Name parsing completeness
        cursor.execute(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN clean_name IS NOT NULL AND clean_name != '' THEN 1 ELSE 0 END) as with_clean_name
            FROM {stage_table}
        """)
        row = cursor.fetchone()
        total, with_clean_name = row[0], row[1]
        checks["name_parsing_completeness"] = {
            "total": total,
            "passed": with_clean_name,
            "failed": total - with_clean_name,
            "description": "All records should have clean_name populated",
        }

        # Rule 2: Status indicator consistency
        cursor.execute(
            f"""
            SELECT
                COUNT(*) as total,
                SUM(
                    CASE WHEN (name LIKE '%$$%' AND is_frozen = true)
                              OR (name NOT LIKE '%$$%' AND is_frozen = false)
                         THEN 1 ELSE 0 END
                ) as consistent_frozen,
                SUM(
                    CASE WHEN (name LIKE '%<%>%' AND is_sponsored = true)
                              OR (name NOT LIKE '%<%>%' AND is_sponsored = false)
                         THEN 1 ELSE 0 END
                ) as consistent_sponsored,
                SUM(
                    CASE WHEN (name LIKE '%{{AF}}%' AND has_admin_fees = true)
                              OR (name NOT LIKE '%{{AF}}%' AND has_admin_fees = false)
                         THEN 1 ELSE 0 END
                ) as consistent_admin_fees
            FROM {stage_table}
        """
        )
        row = cursor.fetchone()
        if row:
            total, consistent_frozen, consistent_sponsored, consistent_admin_fees = row
            avg_consistency = (
                (consistent_frozen + consistent_sponsored + consistent_admin_fees) / (3 * total) if total > 0 else 0
            )
            checks["status_indicator_consistency"] = {
                "total": total * 3,  # 3 checks per record
                "passed": int(avg_consistency * total * 3),
                "failed": int((1 - avg_consistency) * total * 3),
                "description": "Status indicators ($$, <sponsor>, {AF}) should match boolean flags",
                "details": {
                    "frozen_consistency": f"{consistent_frozen}/{total}",
                    "sponsored_consistency": f"{consistent_sponsored}/{total}",
                    "admin_fees_consistency": f"{consistent_admin_fees}/{total}",
                },
            }

        # Rule 3: Birth date validation
        cursor.execute(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN birth_date_normalized IS NOT NULL AND
                              birth_date_normalized >= '1900-01-01' AND
                              birth_date_normalized <= '2010-12-31' THEN 1 ELSE 0 END) as valid_birth_dates
            FROM {stage_table}
            WHERE birthdate IS NOT NULL
        """)
        row = cursor.fetchone()
        if row:
            total, valid_birth_dates = row[0], row[1]
            checks["birth_date_validation"] = {
                "total": total,
                "passed": valid_birth_dates,
                "failed": total - valid_birth_dates,
                "description": "Birth dates should be normalized and within reasonable range (1900-2010)",
            }

        # Rule 4: Emergency contact parsing
        cursor.execute(
            f"""
            SELECT
                COUNT(*) as total,
                SUM(
                    CASE WHEN emg_contactperson IS NOT NULL AND emergency_contact_name IS NOT NULL
                         THEN 1 ELSE 0
                    END
                ) as parsed_contacts
            FROM {stage_table}
            WHERE emg_contactperson IS NOT NULL AND emg_contactperson != ''
        """
        )
        row = cursor.fetchone()
        if row:
            total, parsed_contacts = row[0], row[1]
            checks["emergency_contact_parsing"] = {
                "total": total,
                "passed": parsed_contacts,
                "failed": total - parsed_contacts,
                "description": "Emergency contacts should be parsed when present",
            }

        results["validation_checks"] = checks

    def _validate_academicclasses_business_rules(self, cursor, stage_table: str, results: ValidationResults) -> None:
        """Validate academic classes business rules"""
        checks: dict[str, CheckResult] = {}

        # Rule 1: ClassID format consistency
        cursor.execute(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN classid IS NOT NULL AND LENGTH(classid) >= 3 THEN 1 ELSE 0 END) as valid_classids
            FROM {stage_table}
        """)
        row = cursor.fetchone()
        total, valid_classids = row[0], row[1]
        checks["classid_format"] = {
            "total": total,
            "passed": valid_classids,
            "failed": total - valid_classids,
            "description": "ClassID should be non-null and minimum 3 characters",
        }

        # Rule 2: Term reference validation (if terms table exists)
        if self._table_exists("terms_stage4_valid"):
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN t.termid IS NOT NULL THEN 1 ELSE 0 END) as valid_term_refs
                FROM {stage_table} ac
                LEFT JOIN terms_stage4_valid t ON ac.termid = t.termid
            """)
            row = cursor.fetchone()
            if row:
                total, valid_term_refs = row[0], row[1]
                checks["term_reference_validation"] = {
                    "total": total,
                    "passed": valid_term_refs,
                    "failed": total - valid_term_refs,
                    "description": "All term references should exist in terms table",
                }

        results["validation_checks"] = checks

    def _validate_academiccoursetakers_business_rules(
        self, cursor, stage_table: str, results: ValidationResults
    ) -> None:
        """Validate academic course takers business rules"""
        checks: dict[str, CheckResult] = {}

        # Rule 1: ClassID consistency with academicclasses
        if self._table_exists("academicclasses_stage4_valid"):
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN ac.classid IS NOT NULL THEN 1 ELSE 0 END) as valid_class_refs
                FROM {stage_table} act
                LEFT JOIN academicclasses_stage4_valid ac ON act.classid = ac.classid
            """)
            row = cursor.fetchone()
            if row:
                total, valid_class_refs = row[0], row[1]
                checks["classid_reference_validation"] = {
                    "total": total,
                    "passed": valid_class_refs,
                    "failed": total - valid_class_refs,
                    "description": "All ClassID references should exist in academicclasses table",
                }

        # Rule 2: Student ID validation
        if self._table_exists("students_stage4_valid"):
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END) as valid_student_refs
                FROM {stage_table} act
                LEFT JOIN students_stage4_valid s ON act.studentid = s.id
            """)
            row = cursor.fetchone()
            if row:
                total, valid_student_refs = row[0], row[1]
                checks["student_reference_validation"] = {
                    "total": total,
                    "passed": valid_student_refs,
                    "failed": total - valid_student_refs,
                    "description": "All student references should exist in students table",
                }

        results["validation_checks"] = checks

    def _validate_terms_business_rules(self, cursor, stage_table: str, results: ValidationResults) -> None:
        """Validate terms business rules"""
        checks: dict[str, CheckResult] = {}

        # Rule 1: Date sequence validation
        cursor.execute(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN startdate < enddate THEN 1 ELSE 0 END) as valid_date_sequences
            FROM {stage_table}
            WHERE startdate IS NOT NULL AND enddate IS NOT NULL
        """)
        row = cursor.fetchone()
        if row:
            total, valid_sequences = row[0], row[1]
            checks["date_sequence_validation"] = {
                "total": total,
                "passed": valid_sequences,
                "failed": total - valid_sequences,
                "description": "Term start date should be before end date",
            }

        # Rule 2: Term overlap detection
        cursor.execute(f"""
            SELECT COUNT(*) as overlapping_terms
            FROM {stage_table} t1
            JOIN {stage_table} t2 ON t1.termid != t2.termid
            WHERE t1.startdate < t2.enddate AND t1.enddate > t2.startdate
        """)
        row = cursor.fetchone()
        if row:
            overlapping_count = row[0]
            cursor.execute(f"SELECT COUNT(*) FROM {stage_table}")
            total_terms = cursor.fetchone()[0]

            checks["term_overlap_validation"] = {
                "total": total_terms,
                "passed": total_terms - overlapping_count // 2,  # Each overlap is counted twice
                "failed": overlapping_count // 2,
                "description": "Terms should not have overlapping date ranges",
            }

        results["validation_checks"] = checks

    def _validate_financial_business_rules(
        self, cursor, stage_table: str, results: ValidationResults, table_name: str
    ) -> None:
        """Validate financial tables business rules"""
        checks: dict[str, CheckResult] = {}

        if table_name == "receipt_headers":
            # Rule 1: Positive amounts
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN amount > 0 THEN 1 ELSE 0 END) as positive_amounts
                FROM {stage_table}
                WHERE amount IS NOT NULL
            """)
            row = cursor.fetchone()
            if row:
                total, positive_amounts = row[0], row[1]
                checks["positive_amounts"] = {
                    "total": total,
                    "passed": positive_amounts,
                    "failed": total - positive_amounts,
                    "description": "Receipt amounts should be positive",
                }

        elif table_name == "receipt_items":
            # Rule 1: Item amounts consistency
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN amount IS NOT NULL AND amount != 0 THEN 1 ELSE 0 END) as non_zero_amounts
                FROM {stage_table}
            """)
            row = cursor.fetchone()
            if row:
                total, non_zero_amounts = row[0], row[1]
                checks["non_zero_amounts"] = {
                    "total": total,
                    "passed": non_zero_amounts,
                    "failed": total - non_zero_amounts,
                    "description": "Receipt item amounts should be non-zero",
                }

        results["validation_checks"] = checks

    def _validate_generic_business_rules(self, cursor, stage_table: str, results: ValidationResults) -> None:
        """Validate generic business rules for any table"""
        checks: dict[str, CheckResult] = {}

        # Rule 1: Check for validation errors if column exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = '_validation_errors'
        """,
            [stage_table],
        )

        if cursor.fetchone():
            cursor.execute(
                f"""
                SELECT
                    COUNT(*) as total,
                    SUM(
                        CASE WHEN _validation_errors IS NULL OR _validation_errors = '[]'
                             THEN 1 ELSE 0
                        END
                    ) as no_errors
                FROM {stage_table}
            """
            )
            row = cursor.fetchone()
            if row:
                total, no_errors = row[0], row[1]
                checks["validation_errors_check"] = {
                    "total": total,
                    "passed": no_errors,
                    "failed": total - no_errors,
                    "description": "Records should have no validation errors",
                }

        results["validation_checks"] = checks

    def _show_detailed_results(self, table_name: str, results: ValidationResults, options: dict) -> None:
        """Show detailed validation results"""
        self.stdout.write(f"\n📊 Validation Summary for {table_name}:")
        self.stdout.write(f"   Total Records: {results['total_records']:,}")
        self.stdout.write(f"   Overall Success Rate: {results['overall_success_rate']:.1f}%")

        if results["overall_success_rate"] >= options["threshold"]:
            self.stdout.write(self.style.SUCCESS(f"   Status: ✅ PASS (>= {options['threshold']}%)"))
        else:
            self.stdout.write(self.style.ERROR(f"   Status: ❌ FAIL (< {options['threshold']}%)"))

        # Show individual check results
        self.stdout.write("\n📋 Individual Business Rule Checks:")

        for check_name, check_result in results["validation_checks"].items():
            success_rate = (check_result["passed"] / check_result["total"]) * 100 if check_result["total"] > 0 else 100
            status = "✅" if success_rate >= options["threshold"] else "❌"

            self.stdout.write(f"\n   {status} {check_name.replace('_', ' ').title()}:")
            self.stdout.write(f"      Description: {check_result['description']}")
            self.stdout.write(
                f"      Results: {check_result['passed']:,}/{check_result['total']:,} ({success_rate:.1f}%)"
            )

            if check_result["failed"] > 0:
                self.stdout.write(f"      Failed: {check_result['failed']:,}")

            if "details" in check_result:
                self.stdout.write(f"      Details: {check_result['details']}")

        # Show critical failures
        if results["critical_failures"]:
            self.stdout.write(f"\n🚨 Critical Failures (< {options['threshold']}%):")
            for failure in results["critical_failures"]:
                self.stdout.write(
                    f"   • {failure['check']}: {failure['success_rate']:.1f}% ({failure['failed_count']:,} failures)"
                )

        # Show warnings
        if results["warnings"]:
            self.stdout.write("\n⚠️  Warnings:")
            for warning in results["warnings"]:
                self.stdout.write(f"   • {warning}")

    def _show_overall_summary(self, results: list[tuple[str, dict[str, Any]]], options: dict) -> None:
        """Show overall summary for all tables"""
        self.stdout.write(f"\n{'=' * 80}")
        self.stdout.write("📊 OVERALL BUSINESS RULES VALIDATION SUMMARY")
        self.stdout.write(f"{'=' * 80}")

        total_tables = len(results)
        passing_tables = sum(
            1 for _, result in results if result.get("overall_success_rate", 0) >= options["threshold"]
        )

        self.stdout.write("\nSummary:")
        self.stdout.write(f"   Total Tables: {total_tables}")
        self.stdout.write(f"   Passing Tables: {passing_tables}")
        self.stdout.write(f"   Failing Tables: {total_tables - passing_tables}")
        self.stdout.write(f"   Overall Pass Rate: {(passing_tables / total_tables) * 100:.1f}%")

        if passing_tables == total_tables:
            self.stdout.write(self.style.SUCCESS("\n🎉 All tables passed business rules validation!"))
        else:
            self.stdout.write(self.style.ERROR(f"\n⚠️  {total_tables - passing_tables} tables failed validation"))

        # Show table-by-table summary
        self.stdout.write("\nTable-by-Table Results:")
        for table_name, result in results:
            if "error" in result:
                self.stdout.write(f"   ❌ {table_name}: ERROR - {result['error']}")
            else:
                success_rate = result.get("overall_success_rate", 0)
                status = "✅" if success_rate >= options["threshold"] else "❌"
                record_count = result.get("total_records", 0)
                self.stdout.write(f"   {status} {table_name}: {success_rate:.1f}% ({record_count:,} records)")
