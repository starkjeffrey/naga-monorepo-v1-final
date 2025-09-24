#!/usr/bin/env python3
"""
Management Command Quality Reporter

This script runs quality checks on management commands and reports issues by category:
- Runs mypy type checking
- Runs ruff linting
- Shows quality metrics and trends by category
- Provides focused quality improvement recommendations

Usage:
    python scripts/utilities/report_command_quality.py [--app APP_NAME] [--category CATEGORY] [--detailed]

Options:
    --app: Report only specific app (default: all apps)
    --category: Report only specific category (production/transitional/ephemeral)
    --detailed: Show detailed error messages and line numbers
    --export: Export results to JSON file
"""

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any


class QualityReporter:
    """Runs quality checks and generates reports by command category."""

    CATEGORIES = ["production", "transitional", "ephemeral"]

    def __init__(self) -> None:
        self.backend_path = Path(__file__).parent.parent.parent
        self.results: dict[str, Any] = {
            "mypy": defaultdict(list),
            "ruff": defaultdict(list),
            "stats": defaultdict(dict),
        }

    def run_quality_checks(self, app_name: str | None = None, category: str | None = None) -> dict:
        """Run all quality checks and return results."""
        print("🔍 Running quality checks on management commands...")

        # Get paths to check
        paths_to_check = self._get_paths_to_check(app_name, category)

        if not paths_to_check:
            print("ℹ️  No commands found matching criteria.")
            return self.results

        print(f"📁 Found {len(paths_to_check)} command files to check")

        # Run mypy
        print("\\n🔍 Running mypy type checking...")
        self._run_mypy_checks(paths_to_check)

        # Run ruff
        print("🔍 Running ruff linting...")
        self._run_ruff_checks(paths_to_check)

        # Calculate statistics
        self._calculate_statistics(paths_to_check)

        return self.results

    def _get_paths_to_check(
        self, app_name: str | None = None, category: str | None = None
    ) -> list[tuple[Path, str, str]]:
        """Get all command paths to check with their app and category info."""
        paths = []
        apps_dir = self.backend_path / "apps"

        for app_dir in apps_dir.iterdir():
            if not app_dir.is_dir():
                continue
            if app_name and app_dir.name != app_name:
                continue

            commands_dir = app_dir / "management" / "commands"
            if not commands_dir.exists():
                continue

            # Check categorized commands
            for cat in self.CATEGORIES:
                if category and cat != category:
                    continue

                cat_dir = commands_dir / cat
                if cat_dir.exists():
                    for py_file in cat_dir.glob("*.py"):
                        if py_file.name != "__init__.py":
                            paths.append((py_file, app_dir.name, cat))

            # Check uncategorized commands (root level)
            if not category:  # Only include uncategorized if no category filter
                for py_file in commands_dir.glob("*.py"):
                    if py_file.name != "__init__.py":
                        paths.append((py_file, app_dir.name, "uncategorized"))

        return paths

    def _run_mypy_checks(self, paths: list[tuple[Path, str, str]]):
        """Run mypy type checking on the specified paths."""
        # Group paths by category for appropriate mypy handling
        categorized_paths = defaultdict(list)
        for path, app, category in paths:
            categorized_paths[category].append((path, app))

        for category, cat_paths in categorized_paths.items():
            if category == "ephemeral":
                # Ephemeral commands are excluded from mypy checking
                for path, app in cat_paths:
                    self.results["mypy"][f"{app}/{category}"].append(
                        {
                            "file": path.name,
                            "line": 0,
                            "column": 0,
                            "severity": "note",
                            "message": "Type checking skipped (ephemeral category)",
                            "code": "excluded",
                        }
                    )
                continue

            # Run mypy on non-ephemeral commands
            for path, app in cat_paths:
                try:
                    result = subprocess.run(
                        ["uv", "run", "mypy", str(path), "--show-error-codes"],
                        check=False,
                        capture_output=True,
                        text=True,
                        cwd=self.backend_path,
                    )

                    if result.returncode != 0:
                        # Parse mypy output
                        issues = self._parse_mypy_output(result.stdout)
                        self.results["mypy"][f"{app}/{category}"].extend(issues)

                except subprocess.SubprocessError as e:
                    self.results["mypy"][f"{app}/{category}"].append(
                        {
                            "file": path.name,
                            "line": 0,
                            "column": 0,
                            "severity": "error",
                            "message": f"Failed to run mypy: {e}",
                            "code": "tool-error",
                        }
                    )

    def _run_ruff_checks(self, paths: list[tuple[Path, str, str]]):
        """Run ruff linting on the specified paths."""
        for path, app, category in paths:
            try:
                result = subprocess.run(
                    ["uv", "run", "ruff", "check", str(path), "--output-format=json"],
                    check=False,
                    capture_output=True,
                    text=True,
                    cwd=self.backend_path,
                )

                if result.stdout.strip():
                    # Parse ruff JSON output
                    try:
                        ruff_issues = json.loads(result.stdout)
                        for issue in ruff_issues:
                            self.results["ruff"][f"{app}/{category}"].append(
                                {
                                    "file": issue.get("filename", path.name),
                                    "line": issue.get("location", {}).get("row", 0),
                                    "column": issue.get("location", {}).get("column", 0),
                                    "severity": "error" if issue.get("fix") else "warning",
                                    "message": issue.get("message", "Unknown error"),
                                    "code": issue.get("code", "unknown"),
                                }
                            )
                    except json.JSONDecodeError:
                        # Fallback to plain text parsing
                        issues = self._parse_ruff_output(result.stdout, path.name)
                        self.results["ruff"][f"{app}/{category}"].extend(issues)

            except subprocess.SubprocessError as e:
                self.results["ruff"][f"{app}/{category}"].append(
                    {
                        "file": path.name,
                        "line": 0,
                        "column": 0,
                        "severity": "error",
                        "message": f"Failed to run ruff: {e}",
                        "code": "tool-error",
                    }
                )

    def _parse_mypy_output(self, output: str) -> list[dict]:
        """Parse mypy output into structured issues."""
        issues = []
        for line in output.strip().split("\\n"):
            if ":" in line and ("error:" in line or "warning:" in line or "note:" in line):
                parts = line.split(":", 4)
                if len(parts) >= 4:
                    issues.append(
                        {
                            "file": Path(parts[0]).name,
                            "line": int(parts[1]) if parts[1].isdigit() else 0,
                            "column": int(parts[2]) if parts[2].isdigit() else 0,
                            "severity": "error" if "error:" in line else "warning" if "warning:" in line else "note",
                            "message": parts[3].strip(),
                            "code": "type-check",
                        }
                    )
        return issues

    def _parse_ruff_output(self, output: str, filename: str) -> list[dict]:
        """Parse ruff plain text output into structured issues."""
        issues = []
        for line in output.strip().split("\\n"):
            if filename in line and ":" in line:
                # Try to parse format: filename:line:column: code message
                parts = line.split(":", 3)
                if len(parts) >= 3:
                    issues.append(
                        {
                            "file": filename,
                            "line": int(parts[1]) if parts[1].isdigit() else 0,
                            "column": int(parts[2]) if parts[2].isdigit() else 0,
                            "severity": "warning",
                            "message": parts[3].strip() if len(parts) > 3 else "Linting issue",
                            "code": "lint",
                        }
                    )
        return issues

    def _calculate_statistics(self, paths: list[tuple[Path, str, str]]):
        """Calculate quality statistics by category."""
        stats: dict[str, dict[str, int | float]] = defaultdict(
            lambda: {"files": 0, "mypy_issues": 0, "ruff_issues": 0, "total_issues": 0, "issue_density": 0.0}
        )

        # Count files by category
        for _path, app, category in paths:
            key = f"{app}/{category}"
            stats[key]["files"] += 1

        # Count issues
        for tool in ["mypy", "ruff"]:
            for key, issues in self.results[tool].items():
                tool_key = f"{tool}_issues"
                stats[key][tool_key] = len(issues)
                stats[key]["total_issues"] += len(issues)

        # Calculate density (issues per file)
        for _key, stat in stats.items():
            if stat["files"] > 0:
                stat["issue_density"] = stat["total_issues"] / stat["files"]

        self.results["stats"] = dict(stats)

    def print_report(self, detailed: bool = False):
        """Print a formatted quality report."""
        print("\\n📊 Management Command Quality Report")
        print("=" * 70)

        # Summary statistics
        self._print_summary()

        # Issues by category
        self._print_issues_by_category(detailed)

        # Recommendations
        self._print_recommendations()

    def _print_summary(self):
        """Print summary statistics."""
        total_files = sum(stat["files"] for stat in self.results["stats"].values())
        total_mypy = sum(len(issues) for issues in self.results["mypy"].values())
        total_ruff = sum(len(issues) for issues in self.results["ruff"].values())

        print("\\n📈 Summary:")
        print(f"  Total command files: {total_files}")
        print(f"  MyPy issues: {total_mypy}")
        print(f"  Ruff issues: {total_ruff}")
        print(f"  Total issues: {total_mypy + total_ruff}")

        if total_files > 0:
            density = (total_mypy + total_ruff) / total_files
            print(f"  Average issues per file: {density:.1f}")

    def _print_issues_by_category(self, detailed: bool = False):
        """Print issues organized by category."""
        categories = set()
        for key in self.results["stats"].keys():
            if "/" in key:
                categories.add(key.split("/", 1)[1])

        for category in sorted(categories):
            category_stats = {k: v for k, v in self.results["stats"].items() if k.endswith(f"/{category}")}

            if not category_stats:
                continue

            total_files = sum(stat["files"] for stat in category_stats.values())
            total_issues = sum(stat["total_issues"] for stat in category_stats.values())

            # Category icon
            icon = {"production": "🏭", "transitional": "🔄", "ephemeral": "⚡", "uncategorized": "❓"}.get(
                category, "📁"
            )

            print(f"\\n{icon} {category.title()} Commands:")
            print(f"  Files: {total_files}, Issues: {total_issues}")

            if detailed:
                for key in sorted(category_stats.keys()):
                    app_name = key.split("/", 1)[0]
                    stat = category_stats[key]

                    print(f"\\n    📁 {app_name}:")
                    print(f"      Files: {stat['files']}")
                    print(f"      MyPy: {stat['mypy_issues']}, Ruff: {stat['ruff_issues']}")
                    print(f"      Density: {stat['issue_density']:.1f} issues/file")

                    # Show some example issues
                    mypy_issues = self.results["mypy"].get(key, [])[:3]
                    ruff_issues = self.results["ruff"].get(key, [])[:3]

                    for issue in mypy_issues:
                        print(f"        🔍 {issue['file']}:{issue['line']} - {issue['message']}")

                    for issue in ruff_issues:
                        print(f"        🔧 {issue['file']}:{issue['line']} - {issue['message']}")

    def _print_recommendations(self):
        """Print quality improvement recommendations."""
        print("\\n💡 Recommendations:")

        # Find highest issue categories
        category_totals: dict[str, int] = defaultdict(int)
        for key, stat in self.results["stats"].items():
            if "/" in key:
                category = key.split("/", 1)[1]
                category_totals[category] += stat["total_issues"]

        if category_totals.get("production", 0) > 0:
            print("  • Focus on production command quality - these run in live environments")

        if category_totals.get("transitional", 0) > 20:
            print("  • Consider cleaning up transitional commands or moving to ephemeral")

        if category_totals.get("uncategorized", 0) > 0:
            print("  • Run move_management_commands.py to categorize uncategorized commands")

        # Type checking recommendations
        total_mypy = sum(len(issues) for issues in self.results["mypy"].values())
        if total_mypy > 0:
            print(f"  • Add type hints to reduce {total_mypy} type checking issues")

        # Linting recommendations
        total_ruff = sum(len(issues) for issues in self.results["ruff"].values())
        if total_ruff > 0:
            print(f"  • Run 'uv run ruff check --fix' to auto-fix {total_ruff} linting issues")

    def export_results(self, filename: str):
        """Export results to JSON file."""
        output_path = self.backend_path / filename

        # Convert defaultdicts to regular dicts for JSON serialization
        export_data = {
            "mypy": dict(self.results["mypy"]),
            "ruff": dict(self.results["ruff"]),
            "stats": dict(self.results["stats"]),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)

        print(f"\\n💾 Results exported to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Report on management command quality")
    parser.add_argument("--app", type=str, help="Report only specific app (default: all apps)")
    parser.add_argument(
        "--category", choices=["production", "transitional", "ephemeral"], help="Report only specific category"
    )
    parser.add_argument("--detailed", action="store_true", help="Show detailed error messages and line numbers")
    parser.add_argument("--export", type=str, help="Export results to JSON file")

    args = parser.parse_args()

    reporter = QualityReporter()

    # Run quality checks
    reporter.run_quality_checks(args.app, args.category)

    # Print report
    reporter.print_report(args.detailed)

    # Export if requested
    if args.export:
        reporter.export_results(args.export)


if __name__ == "__main__":
    main()
