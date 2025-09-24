"""
Validate Configurations Management Command

Validates all table configurations to ensure they are correct before pipeline execution.
Checks for missing dependencies, invalid rules, and configuration consistency.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.data_pipeline.core.registry import get_registry


class Command(BaseCommand):
    help = "Validate all table configurations and dependencies"

    def add_arguments(self, parser):
        parser.add_argument("--table", help="Validate specific table (default: all tables)")
        parser.add_argument("--check-dependencies", action="store_true", help="Check dependency resolution order")
        parser.add_argument("--check-files", action="store_true", help="Check if source files exist")
        parser.add_argument(
            "--source-dir", default="data/legacy/data-pipeline/inputs", help="Source directory for file checking"
        )
        parser.add_argument(
            "--output-format",
            choices=["summary", "detailed", "json"],
            default="summary",
            help="Output format (default: summary)",
        )

    def handle(self, *args, **options):
        """Main command handler"""
        try:
            if options["table"]:
                # Validate single table
                results = self._validate_single_table(options["table"], options)
            else:
                # Validate all tables
                results = self._validate_all_tables(options)

            # Display results
            if options["output_format"] == "json":
                self._output_json(results)
            elif options["output_format"] == "detailed":
                self._output_detailed(results)
            else:
                self._output_summary(results)

            # Exit with error code if validation failed
            if results.get("has_errors", False):
                raise CommandError("Configuration validation failed")

        except Exception as e:
            raise CommandError(f"Validation failed: {e!s}") from e

    def _validate_single_table(self, table_name: str, options: dict) -> dict:
        """Validate a single table configuration"""
        try:
            config = get_registry().get_config(table_name)
        except ValueError as e:
            return {"table": table_name, "has_errors": True, "errors": [str(e)], "warnings": [], "details": {}}

        return self._validate_table_config(config, options)

    def _validate_all_tables(self, options: dict) -> dict:
        """Validate all registered table configurations"""
        reg = get_registry()
        table_names = reg.list_tables()
        all_configs = {name: reg.get_config(name) for name in table_names}

        if not all_configs:
            return {"has_errors": True, "errors": ["No table configurations found"], "warnings": [], "tables": {}}

        results: dict[str, Any] = {"has_errors": False, "errors": [], "warnings": [], "tables": {}, "summary": {}}

        # Validate each table
        for table_name, config in all_configs.items():
            table_result = self._validate_table_config(config, options)
            results["tables"][table_name] = table_result

            if table_result["has_errors"]:
                results["has_errors"] = True
                results["errors"].extend([f"{table_name}: {err}" for err in table_result["errors"]])

            results["warnings"].extend([f"{table_name}: {warn}" for warn in table_result["warnings"]])

        # Global validations
        if options["check_dependencies"]:
            dep_result = self._validate_dependencies(all_configs)
            results["dependencies"] = dep_result
            if dep_result["has_errors"]:
                results["has_errors"] = True
                results["errors"].extend(dep_result["errors"])

        # Generate summary
        results["summary"] = self._generate_summary(results["tables"])

        return results

    def _validate_table_config(self, config, options: dict) -> dict:
        """Validate a single table configuration"""
        errors = []
        warnings = []
        details = {}

        # Basic configuration validation
        try:
            config_errors = config.validate()
            errors.extend(config_errors)
        except Exception as e:
            errors.append(f"Configuration validation failed: {e!s}")

        # Check column mappings
        column_result = self._validate_column_mappings(config)
        details["columns"] = column_result
        errors.extend(column_result["errors"])
        warnings.extend(column_result["warnings"])

        # Check validator class
        validator_result = self._validate_validator_class(config)
        details["validator"] = validator_result
        errors.extend(validator_result["errors"])
        warnings.extend(validator_result["warnings"])

        # Check cleaning rules
        cleaning_result = self._validate_cleaning_rules(config)
        details["cleaning_rules"] = cleaning_result
        errors.extend(cleaning_result["errors"])
        warnings.extend(cleaning_result["warnings"])

        # Check source files if requested
        if options["check_files"]:
            file_result = self._validate_source_files(config, options["source_dir"])
            details["files"] = file_result
            errors.extend(file_result["errors"])
            warnings.extend(file_result["warnings"])

        # Check table names don't conflict with PostgreSQL reserved words
        table_result = self._validate_table_names(config)
        details["table_names"] = table_result
        errors.extend(table_result["errors"])
        warnings.extend(table_result["warnings"])

        return {
            "table": config.table_name,
            "has_errors": len(errors) > 0,
            "errors": errors,
            "warnings": warnings,
            "details": details,
        }

    def _validate_column_mappings(self, config) -> dict:
        """Validate column mappings"""
        errors: list[str] = []
        warnings: list[str] = []
        details: dict[str, Any] = {"total_columns": len(config.column_mappings)}

        if not config.column_mappings:
            errors.append("No column mappings defined")
            return {"errors": errors, "warnings": warnings, "details": details}

        # Check for duplicate source names
        source_names = [cm.source_name for cm in config.column_mappings]
        if len(source_names) != len(set(source_names)):
            duplicates = [name for name in source_names if source_names.count(name) > 1]
            errors.append(f"Duplicate source column names: {set(duplicates)}")

        # Check for duplicate target names
        target_names = [cm.target_name for cm in config.column_mappings]
        if len(target_names) != len(set(target_names)):
            duplicates = [name for name in target_names if target_names.count(name) > 1]
            errors.append(f"Duplicate target column names: {set(duplicates)}")

        # Validate individual mappings
        invalid_mappings = 0
        for mapping in config.column_mappings:
            try:
                # Check required fields
                if not mapping.source_name or not mapping.target_name:
                    invalid_mappings += 1
                    continue

                # Check target name is valid PostgreSQL identifier
                if not self._is_valid_postgres_identifier(mapping.target_name):
                    warnings.append(f"Target name '{mapping.target_name}' may not be valid PostgreSQL identifier")

            except Exception:
                invalid_mappings += 1

        if invalid_mappings > 0:
            errors.append(f"{invalid_mappings} invalid column mappings found")

        details["invalid_mappings"] = invalid_mappings
        details["required_columns"] = len([cm for cm in config.column_mappings if not cm.nullable])

        return {"errors": errors, "warnings": warnings, "details": details}

    def _validate_validator_class(self, config) -> dict:
        """Validate Pydantic validator class"""
        errors: list[str] = []
        warnings: list[str] = []
        details: dict[str, Any] = {}

        if not config.validator_class:
            errors.append("No validator class specified")
            return {"errors": errors, "warnings": warnings, "details": details}

        try:
            # Check if it's a Pydantic model
            from pydantic import BaseModel

            if not issubclass(config.validator_class, BaseModel):
                errors.append("Validator class must inherit from pydantic.BaseModel")
            else:
                # Test instantiation with empty data
                try:
                    config.validator_class()
                    details["can_instantiate_empty"] = True
                except Exception as e:
                    details["can_instantiate_empty"] = False
                    details["instantiation_error"] = str(e)

                # Get field information
                if hasattr(config.validator_class, "__fields__"):
                    fields = config.validator_class.__fields__
                    details["field_count"] = len(fields)
                    details["required_fields"] = [
                        name for name, field in fields.items() if hasattr(field, "is_required") and field.is_required()
                    ]
                    details["optional_fields"] = [
                        name
                        for name, field in fields.items()
                        if hasattr(field, "is_required") and not field.is_required()
                    ]

        except ImportError:
            errors.append("Pydantic not available - cannot validate validator class")
        except Exception as e:
            errors.append(f"Error validating validator class: {e!s}")

        return {"errors": errors, "warnings": warnings, "details": details}

    def _validate_cleaning_rules(self, config) -> dict:
        """Validate cleaning rules configuration"""
        errors: list[str] = []
        warnings: list[str] = []
        details: dict[str, Any] = {}

        # Check if cleaning rules engine can be imported
        try:
            from apps.data_pipeline.cleaners.engine import CleaningEngine

            engine = CleaningEngine(config.cleaning_rules)
            available_rules = engine.get_available_rules()
            details["available_rules"] = available_rules

            # Check all column mapping rules are valid
            invalid_rules = []
            for mapping in config.column_mappings:
                for rule in mapping.cleaning_rules:
                    if rule not in available_rules:
                        invalid_rules.append(f"{mapping.source_name}: {rule}")

            if invalid_rules:
                errors.append(f"Invalid cleaning rules: {invalid_rules}")

            details["total_rule_applications"] = sum(len(cm.cleaning_rules) for cm in config.column_mappings)

        except Exception as e:
            errors.append(f"Cannot validate cleaning rules: {e!s}")

        return {"errors": errors, "warnings": warnings, "details": details}

    def _validate_source_files(self, config, source_dir: str) -> dict:
        """Validate source files exist and are readable"""
        errors: list[str] = []
        warnings: list[str] = []
        details: dict[str, Any] = {}

        from pathlib import Path

        source_path = Path(source_dir)
        if not source_path.exists():
            errors.append(f"Source directory does not exist: {source_dir}")
            return {"errors": errors, "warnings": warnings, "details": details}

        # Check source file exists
        source_file = source_path / config.source_file_pattern

        if not source_file.exists():
            errors.append(f"Source file not found: {source_file}")
        else:
            try:
                # Basic file checks
                file_size = source_file.stat().st_size
                details["file_size"] = file_size

                if file_size == 0:
                    warnings.append("Source file is empty")
                elif file_size > 1024 * 1024 * 1024:  # 1GB
                    warnings.append(f"Source file is very large: {file_size / (1024 * 1024):.1f}MB")

                # Try to read first few lines
                with open(source_file, encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline().strip()
                    if first_line:
                        details["estimated_columns"] = len(first_line.split(","))

                        # Compare with configured columns
                        if config.column_mappings:
                            expected_columns = len(config.column_mappings)
                            if details["estimated_columns"] != expected_columns:
                                warnings.append(
                                    f"Column count mismatch: file has ~{details['estimated_columns']}, "
                                    f"config has {expected_columns}"
                                )

                details["file_exists"] = True

            except Exception as e:
                errors.append(f"Cannot read source file: {e!s}")

        return {"errors": errors, "warnings": warnings, "details": details}

    def _validate_table_names(self, config) -> dict:
        """Validate table names don't conflict with reserved words"""
        errors = []
        warnings = []
        details = {}

        # PostgreSQL reserved words (subset)
        pg_reserved = {
            "user",
            "table",
            "index",
            "where",
            "select",
            "from",
            "order",
            "group",
            "having",
            "union",
            "intersect",
            "except",
            "distinct",
            "limit",
            "offset",
        }

        table_names = [config.raw_table_name, config.cleaned_table_name, config.validated_table_name]

        for table_name in table_names:
            if table_name.lower() in pg_reserved:
                errors.append(f"Table name '{table_name}' conflicts with PostgreSQL reserved word")

            if not self._is_valid_postgres_identifier(table_name):
                warnings.append(f"Table name '{table_name}' may not be valid PostgreSQL identifier")

        details["table_names"] = table_names

        return {"errors": errors, "warnings": warnings, "details": details}

    def _validate_dependencies(self, all_configs: dict) -> dict:
        """Validate dependency resolution"""
        errors: list[str] = []
        warnings: list[str] = []
        details: dict[str, Any] = {}

        try:
            # Get dependency order from registry
            from apps.data_pipeline.core.registry import get_registry

            dependency_order = get_registry().get_pipeline_order()
            details["dependency_order"] = dependency_order

            # Check for circular dependencies (simple check)
            tables_with_deps: list[tuple[str, list[str]]] = []
            for table_name, config in all_configs.items():
                deps = getattr(config, "dependencies", [])
                if deps:
                    tables_with_deps.append((table_name, deps))

            details["tables_with_dependencies"] = tables_with_deps

            # Check all dependencies exist
            for table_name, deps in tables_with_deps:
                for dep in deps:
                    if dep not in all_configs:
                        errors.append(f"Table '{table_name}' depends on non-existent table '{dep}'")

        except Exception as e:
            errors.append(f"Error validating dependencies: {e!s}")

        return {"has_errors": len(errors) > 0, "errors": errors, "warnings": warnings, "details": details}

    def _is_valid_postgres_identifier(self, name: str) -> bool:
        """Check if name is valid PostgreSQL identifier"""
        import re

        if not name:
            return False

        # Must start with letter or underscore
        if not re.match(r"^[a-zA-Z_]", name):
            return False

        # Can only contain letters, digits, underscores
        if not re.match(r"^[a-zA-Z0-9_]*$", name):
            return False

        # Must not be too long (PostgreSQL limit is 63 characters)
        if len(name) > 63:
            return False

        return True

    def _generate_summary(self, table_results: dict) -> dict:
        """Generate validation summary statistics"""
        total_tables = len(table_results)
        tables_with_errors = sum(1 for r in table_results.values() if r["has_errors"])
        tables_with_warnings = sum(1 for r in table_results.values() if r["warnings"])

        total_errors = sum(len(r["errors"]) for r in table_results.values())
        total_warnings = sum(len(r["warnings"]) for r in table_results.values())

        return {
            "total_tables": total_tables,
            "tables_with_errors": tables_with_errors,
            "tables_with_warnings": tables_with_warnings,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "success_rate": ((total_tables - tables_with_errors) / total_tables * 100) if total_tables > 0 else 0,
        }

    def _output_summary(self, results: dict):
        """Output summary format"""
        self.stdout.write("=" * 60)
        self.stdout.write("CONFIGURATION VALIDATION SUMMARY")
        self.stdout.write("=" * 60)

        if "summary" in results:
            summary = results["summary"]
            self.stdout.write(f"Tables validated: {summary['total_tables']}")
            self.stdout.write(f"Tables with errors: {summary['tables_with_errors']}")
            self.stdout.write(f"Tables with warnings: {summary['tables_with_warnings']}")
            self.stdout.write(f"Success rate: {summary['success_rate']:.1f}%")
            self.stdout.write("")

        # Show errors
        if results.get("has_errors"):
            self.stdout.write(self.style.ERROR("❌ ERRORS FOUND:"))
            for error in results.get("errors", []):
                self.stdout.write(f"   • {error}")
            self.stdout.write("")

        # Show warnings
        if results.get("warnings"):
            self.stdout.write(self.style.WARNING("⚠️  WARNINGS:"))
            for warning in results.get("warnings", []):
                self.stdout.write(f"   • {warning}")
            self.stdout.write("")

        # Per-table status
        if "tables" in results:
            self.stdout.write("Per-table status:")
            for table_name, table_result in results["tables"].items():
                status = "❌" if table_result["has_errors"] else "✅"
                error_count = len(table_result["errors"])
                warning_count = len(table_result["warnings"])

                status_text = f"{status} {table_name}"
                if error_count > 0:
                    status_text += f" ({error_count} errors)"
                if warning_count > 0:
                    status_text += f" ({warning_count} warnings)"

                self.stdout.write(f"   {status_text}")

        if not results.get("has_errors"):
            self.stdout.write(self.style.SUCCESS("\n🎉 All configurations are valid!"))

    def _output_detailed(self, results: dict):
        """Output detailed format"""
        # Start with summary
        self._output_summary(results)

        # Add detailed breakdown
        if "tables" in results:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("DETAILED VALIDATION RESULTS")
            self.stdout.write("=" * 60)

            for table_name, table_result in results["tables"].items():
                self.stdout.write(f"\n📋 Table: {table_name}")
                self.stdout.write("-" * 40)

                # Show details
                if "details" in table_result:
                    details = table_result["details"]

                    if "columns" in details:
                        col_details = details["columns"]["details"]
                        self.stdout.write(f"   Columns: {col_details.get('total_columns', 0)}")
                        self.stdout.write(f"   Required columns: {col_details.get('required_columns', 0)}")

                    if "validator" in details:
                        val_details = details["validator"]["details"]
                        if "field_count" in val_details:
                            self.stdout.write(f"   Validator fields: {val_details['field_count']}")

                    if "files" in details:
                        file_details = details["files"]["details"]
                        if "file_size" in file_details:
                            size_mb = file_details["file_size"] / (1024 * 1024)
                            self.stdout.write(f"   Source file size: {size_mb:.2f}MB")

                # Show errors for this table
                if table_result["errors"]:
                    self.stdout.write("   ❌ Errors:")
                    for error in table_result["errors"]:
                        self.stdout.write(f"      • {error}")

                # Show warnings for this table
                if table_result["warnings"]:
                    self.stdout.write("   ⚠️  Warnings:")
                    for warning in table_result["warnings"]:
                        self.stdout.write(f"      • {warning}")

    def _output_json(self, results: dict):
        """Output JSON format"""
        import json

        self.stdout.write(json.dumps(results, indent=2, default=str))
