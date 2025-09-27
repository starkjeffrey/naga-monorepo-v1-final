#!/usr/bin/env python3
"""
Management Command Structure Validator

This script validates the categorized management command structure:
- Verifies directory structure exists
- Checks for proper __init__.py files
- Validates command categorization
- Reports on structure compliance

Usage:
    python scripts/utilities/validate_command_structure.py [--app APP_NAME] [--fix]

Options:
    --app: Validate only specific app (default: all apps)
    --fix: Automatically fix simple issues like missing __init__.py files
"""

import argparse
from pathlib import Path
from typing import Any


class StructureValidator:
    """Validates the management command directory structure."""

    EXPECTED_CATEGORIES = ["production", "transitional", "ephemeral"]

    def __init__(self):
        self.backend_path = Path(__file__).parent.parent.parent
        self.issues = []
        self.stats = {"apps_checked": 0, "commands_found": 0, "issues_found": 0, "issues_fixed": 0}

    def validate_all_apps(self, app_name: str | None = None, fix: bool = False) -> dict:
        """Validate all apps or a specific app."""
        apps_dir = self.backend_path / "apps"

        for app_dir in apps_dir.iterdir():
            if not app_dir.is_dir():
                continue
            if app_name and app_dir.name != app_name:
                continue

            self.validate_app(app_dir, fix)
            self.stats["apps_checked"] += 1

        return self.get_summary()

    def validate_app(self, app_path: Path, fix: bool = False):
        """Validate the structure for a single app."""
        app_name = app_path.name
        commands_dir = app_path / "management" / "commands"

        if not commands_dir.exists():
            self.add_issue(f"{app_name}: No management/commands directory found")
            return

        # Check for old-style flat commands (in root of commands/)
        self._check_flat_commands(app_name, commands_dir)

        # Check category directories
        for category in self.EXPECTED_CATEGORIES:
            category_dir = commands_dir / category
            self._validate_category_directory(app_name, category, category_dir, fix)

        # Check for unknown directories
        self._check_unknown_directories(app_name, commands_dir)

    def _check_flat_commands(self, app_name: str, commands_dir: Path):
        """Check for commands still in the root commands directory."""
        flat_commands = []

        for item in commands_dir.iterdir():
            if item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
                flat_commands.append(item.name)
                self.stats["commands_found"] += 1

        if flat_commands:
            self.add_issue(
                f"{app_name}: {len(flat_commands)} uncategorized commands found",
                "warning",
                {"commands": flat_commands, "suggestion": "Run move_management_commands.py to categorize these"},
            )

    def _validate_category_directory(self, app_name: str, category: str, category_dir: Path, fix: bool = False):
        """Validate a specific category directory."""
        if not category_dir.exists():
            self.add_issue(
                f"{app_name}: Missing {category}/ directory",
                "info",
                {"suggestion": "Directory will be created when commands are moved"},
            )
            return

        # Check for __init__.py
        init_file = category_dir / "__init__.py"
        if not init_file.exists():
            self.add_issue(f"{app_name}: Missing __init__.py in {category}/", "error" if not fix else "fixed")

            if fix:
                self._create_init_file(category_dir, category)
                self.stats["issues_fixed"] += 1
        else:
            # Validate __init__.py content
            self._validate_init_content(app_name, category, init_file, fix)

        # Count commands in this category
        command_count = len([f for f in category_dir.glob("*.py") if f.name != "__init__.py"])
        if command_count > 0:
            self.stats["commands_found"] += command_count

        # Check for non-Python files
        non_python_files = [f for f in category_dir.iterdir() if f.is_file() and f.suffix != ".py"]
        if non_python_files:
            self.add_issue(
                f"{app_name}: Non-Python files in {category}/",
                "warning",
                {"files": [f.name for f in non_python_files]},
            )

    def _validate_init_content(self, app_name: str, category: str, init_file: Path, fix: bool = False):
        """Validate the content of __init__.py files."""
        try:
            content = init_file.read_text(encoding="utf-8")
            expected_keywords = {
                "production": ["operational", "maintenance", "quality standards"],
                "transitional": ["migration", "setup", "temporary"],
                "ephemeral": ["analysis", "debugging", "relaxed", "excluded"],
            }

            keywords = expected_keywords.get(category, [])
            missing_keywords = [kw for kw in keywords if kw.lower() not in content.lower()]

            if missing_keywords or len(content.strip()) < 50:
                issue_type = "fixed" if fix else "warning"
                self.add_issue(
                    f"{app_name}: Incomplete documentation in {category}/__init__.py",
                    issue_type,
                    {"missing_keywords": missing_keywords},
                )

                if fix:
                    self._create_init_file(init_file.parent, category)
                    self.stats["issues_fixed"] += 1

        except Exception as e:
            self.add_issue(f"{app_name}: Error reading {category}/__init__.py: {e}", "error")

    def _check_unknown_directories(self, app_name: str, commands_dir: Path):
        """Check for directories that aren't part of the standard structure."""
        unknown_dirs = []

        for item in commands_dir.iterdir():
            if item.is_dir() and item.name not in self.EXPECTED_CATEGORIES and item.name != "__pycache__":
                unknown_dirs.append(item.name)

        if unknown_dirs:
            self.add_issue(
                f"{app_name}: Unknown directories in commands/",
                "warning",
                {"directories": unknown_dirs, "suggestion": "Consider moving commands to standard categories"},
            )

    def _create_init_file(self, category_dir: Path, category: str):
        """Create a proper __init__.py file for a category."""
        contents = {
            "production": '''"""
Production management commands.

Commands in this directory are for ongoing operational needs:
- User-facing operations
- Regular maintenance tasks
- Data processing workflows
- Reporting and analytics

All commands here must meet full code quality standards.
"""''',
            "transitional": '''"""
Transitional management commands.

Commands in this directory are for setup and migration tasks:
- Data migration scripts
- System initialization
- One-time setup operations
- Schema transformations

These commands are temporary but important, requiring good quality standards.
"""''',
            "ephemeral": '''"""
Ephemeral management commands.

Commands in this directory are for quick analysis and fixes:
- One-off debugging scripts
- Data exploration tools
- Experimental analysis
- Quick fixes and patches

Quality standards are relaxed for these commands to allow for rapid development.
They are excluded from type checking and strict linting.
"""''',
        }

        init_file = category_dir / "__init__.py"
        init_file.write_text(contents[category], encoding="utf-8")

    def add_issue(self, message: str, level: str = "info", details: dict | None = None):
        """Add an issue to the report."""
        issue = {"message": message, "level": level, "details": details or {}}
        self.issues.append(issue)

        if level in ["error", "warning"]:
            self.stats["issues_found"] += 1

    def get_summary(self) -> dict:
        """Get validation summary."""
        return {"stats": self.stats, "issues": self.issues, "issues_by_level": self._group_issues_by_level()}

    def _group_issues_by_level(self) -> dict[str, list]:
        """Group issues by severity level."""
        grouped: dict[str, list[dict[str, Any]]] = {"error": [], "warning": [], "info": [], "fixed": []}

        for issue in self.issues:
            level = issue["level"]
            if level in grouped:
                grouped[level].append(issue)

        return grouped

    def print_report(self, summary: dict, verbose: bool = False):
        """Print a formatted validation report."""
        stats = summary["stats"]
        issues_by_level = summary["issues_by_level"]

        print("📋 Management Command Structure Validation Report")
        print("=" * 60)

        # Statistics
        print("\\n📊 Statistics:")
        print(f"  Apps checked: {stats['apps_checked']}")
        print(f"  Commands found: {stats['commands_found']}")
        print(f"  Issues found: {stats['issues_found']}")
        if stats["issues_fixed"] > 0:
            print(f"  Issues fixed: {stats['issues_fixed']}")

        # Issues by level
        for level in ["error", "warning", "info", "fixed"]:
            issues = issues_by_level.get(level, [])
            if not issues:
                continue

            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️", "fixed": "✅"}[level]
            print(f"\\n{icon} {level.title()} ({len(issues)}):")

            for issue in issues:
                print(f"  • {issue['message']}")

                if verbose and issue["details"]:
                    for key, value in issue["details"].items():
                        if isinstance(value, list):
                            print(f"    {key}: {', '.join(value)}")
                        else:
                            print(f"    {key}: {value}")

        # Overall status
        error_count = len(issues_by_level.get("error", []))
        warning_count = len(issues_by_level.get("warning", []))

        print(f"\\n{'=' * 60}")
        if error_count == 0 and warning_count == 0:
            print("✅ Structure validation passed!")
        elif error_count == 0:
            print(f"⚠️  Structure mostly valid ({warning_count} warnings)")
        else:
            print(f"❌ Structure needs attention ({error_count} errors, {warning_count} warnings)")

        # Recommendations
        if stats["commands_found"] == 0:
            print("\\n💡 No management commands found. This might be expected for some apps.")
        elif any("uncategorized commands" in issue["message"] for issue in self.issues):
            print("\\n💡 Next steps:")
            print("   1. Run move_management_commands.py to categorize uncategorized commands")
            print("   2. Re-run this validation script to verify structure")


def main():
    parser = argparse.ArgumentParser(description="Validate management command structure")
    parser.add_argument("--app", type=str, help="Validate only specific app (default: all apps)")
    parser.add_argument(
        "--fix", action="store_true", help="Automatically fix simple issues like missing __init__.py files"
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed information about issues")

    args = parser.parse_args()

    validator = StructureValidator()

    print("Validating management command structure...")
    if args.fix:
        print("🔧 Fix mode enabled - will repair simple issues")

    summary = validator.validate_all_apps(args.app, args.fix)
    validator.print_report(summary, args.verbose)


if __name__ == "__main__":
    main()
