#!/usr/bin/env python3
"""
Code Quality Analysis Script
Analyzes MyPy and Ruff errors and creates comprehensive breakdown reports
"""

import argparse
import re
import subprocess
from collections import Counter
from pathlib import Path


class CodeQualityAnalyzer:
    """Analyzes MyPy and Ruff errors to provide actionable reports."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()

    def run_mypy_analysis(self) -> dict:
        """Run MyPy analysis and return structured results."""
        print("🔍 Running MyPy analysis...")

        try:
            # Run MyPy and capture output
            result = subprocess.run(
                ["uv", "run", "mypy", "."],
                check=False,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            errors_by_type: Counter[str] = Counter()
            errors_by_folder: Counter[str] = Counter()
            errors_by_file: Counter[str] = Counter()

            # Parse MyPy output - check both stderr and stdout
            error_pattern = re.compile(r"^([^:]+):(\d+):(?:\d+:)?\s*(error|note):\s*(.+?)\s*\[([^\]]+)\]")

            # Combine stderr and stdout for parsing
            mypy_output = result.stderr + "\n" + result.stdout

            for line in mypy_output.split("\n"):
                line = line.strip()
                if not line:
                    continue

                match = error_pattern.match(line)
                if match:
                    file_path, _line_num, severity, _message, error_code = match.groups()

                    # Only count errors, not notes
                    if severity == "error":
                        errors_by_type[error_code] += 1

                        # Count by folder
                        path_obj = Path(file_path)
                        if path_obj.parts:
                            folder = path_obj.parts[0] if len(path_obj.parts) > 1 else "root"
                            errors_by_folder[folder] += 1

                        errors_by_file[file_path] += 1

            # Extract total from summary line
            total_errors = 0
            for line in mypy_output.split("\n"):
                if "Found" in line and "errors" in line:
                    match = re.search(r"Found (\d+) errors", line)
                    if match:
                        total_errors = int(match.group(1))
                        break

            return {
                "total_errors": total_errors,
                "errors_by_type": errors_by_type,
                "errors_by_folder": errors_by_folder,
                "errors_by_file": errors_by_file,
                "raw_output": mypy_output,
            }

        except subprocess.TimeoutExpired:
            print("⚠️ MyPy analysis timed out")
            return {
                "total_errors": 0,
                "errors_by_type": Counter(),
                "errors_by_folder": Counter(),
                "errors_by_file": Counter(),
                "raw_output": "Timeout",
            }
        except Exception as e:
            print(f"❌ MyPy analysis failed: {e}")
            return {
                "total_errors": 0,
                "errors_by_type": Counter(),
                "errors_by_folder": Counter(),
                "errors_by_file": Counter(),
                "raw_output": str(e),
            }

    def run_ruff_analysis(self) -> dict:
        """Run Ruff analysis and return structured results."""
        print("🔍 Running Ruff analysis...")

        try:
            # Run Ruff and capture output
            result = subprocess.run(
                ["uv", "run", "ruff", "check", "--output-format=json"],
                check=False,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            errors_by_type: Counter[str] = Counter()
            errors_by_folder: Counter[str] = Counter()
            errors_by_file: Counter[str] = Counter()

            # Parse JSON output if available
            import json

            try:
                if result.stdout.strip():
                    ruff_data = json.loads(result.stdout)

                    for error in ruff_data:
                        file_path = error.get("filename", "")
                        error_code = error.get("code", "unknown")

                        errors_by_type[error_code] += 1

                        # Count by folder
                        if file_path:
                            path_obj = Path(file_path)
                            if path_obj.parts:
                                folder = path_obj.parts[0] if len(path_obj.parts) > 1 else "root"
                                errors_by_folder[folder] += 1

                            errors_by_file[file_path] += 1
            except json.JSONDecodeError:
                # Fall back to text parsing
                for line in result.stdout.split("\n"):
                    if ":" in line and any(char.isdigit() for char in line):
                        # Parse text format: file:line:col: CODE message
                        match = re.match(r"^([^:]+):\d+:\d+:\s*([A-Z]\d+)", line)
                        if match:
                            file_path, error_code = match.groups()
                            errors_by_type[error_code] += 1

                            path_obj = Path(file_path)
                            if path_obj.parts:
                                folder = path_obj.parts[0] if len(path_obj.parts) > 1 else "root"
                                errors_by_folder[folder] += 1

                            errors_by_file[file_path] += 1

            total_errors = sum(errors_by_type.values())

            return {
                "total_errors": total_errors,
                "errors_by_type": errors_by_type,
                "errors_by_folder": errors_by_folder,
                "errors_by_file": errors_by_file,
                "raw_output": result.stdout or result.stderr,
            }

        except subprocess.TimeoutExpired:
            print("⚠️ Ruff analysis timed out")
            return {
                "total_errors": 0,
                "errors_by_type": Counter(),
                "errors_by_folder": Counter(),
                "errors_by_file": Counter(),
                "raw_output": "Timeout",
            }
        except Exception as e:
            print(f"❌ Ruff analysis failed: {e}")
            return {
                "total_errors": 0,
                "errors_by_type": Counter(),
                "errors_by_folder": Counter(),
                "errors_by_file": Counter(),
                "raw_output": str(e),
            }

    def generate_mypy_report(self, analysis_results: dict) -> str:
        """Generate detailed MyPy error report."""
        total_errors = analysis_results["total_errors"]
        errors_by_type = analysis_results["errors_by_type"]
        errors_by_folder = analysis_results["errors_by_folder"]
        errors_by_file = analysis_results["errors_by_file"]

        report = f"""# MyPy Error Analysis Report

## Executive Summary
- **Total MyPy Errors:** {total_errors:,}
- **Unique Error Types:** {len(errors_by_type)}
- **Affected Folders:** {len(errors_by_folder)}
- **Affected Files:** {len(errors_by_file)}

## Error Breakdown by Type

| Error Code | Count | Percentage | Priority | Description |
|------------|-------|------------|----------|-------------|
"""

        # Sort by count (descending)
        for error_type, count in errors_by_type.most_common(20):
            percentage = (count / total_errors) * 100 if total_errors > 0 else 0
            priority = self._get_mypy_priority(error_type)
            description = self._get_mypy_description(error_type)
            report += f"| `{error_type}` | {count:,} | {percentage:.1f}% | {priority} | {description} |\n"

        if len(errors_by_type) > 20:
            other_count = sum(count for _, count in errors_by_type.most_common()[20:])
            report += f"| ... | {other_count:,} | ... | ... | Other error types |\n"

        report += """
## Error Breakdown by Folder

| Folder | Count | Percentage | Repair Target |
|--------|-------|------------|---------------|
"""

        for folder, count in errors_by_folder.most_common(10):
            percentage = (count / total_errors) * 100 if total_errors > 0 else 0
            target_level = "🔴 High" if count > 200 else "🟡 Medium" if count > 50 else "🟢 Low"
            report += f"| `{folder}/` | {count:,} | {percentage:.1f}% | {target_level} |\n"

        report += """
## Top 15 Most Problematic Files

| File | Error Count | Top Error Types |
|------|-------------|-----------------|
"""

        # Get top 15 files by error count
        for file_path, count in errors_by_file.most_common(15):
            short_path = file_path.replace(str(self.project_root) + "/", "")
            report += f"| `{short_path}` | {count} | _See detailed analysis_ |\n"

        report += """
## Repair Recommendations

### 🔴 High Priority (Quick Wins)
"""

        high_priority_types = [
            (t, c) for t, c in errors_by_type.most_common(10) if self._get_mypy_priority(t) == "🔴 High"
        ]
        for error_type, count in high_priority_types:
            report += f"- **{error_type}** ({count} errors): {self._get_mypy_fix_suggestion(error_type)}\n"

        report += """
### 🟡 Medium Priority (Systematic Fixes)
"""

        medium_priority_types = [
            (t, c) for t, c in errors_by_type.most_common(20) if self._get_mypy_priority(t) == "🟡 Medium"
        ][:5]
        for error_type, count in medium_priority_types:
            report += f"- **{error_type}** ({count} errors): {self._get_mypy_fix_suggestion(error_type)}\n"

        report += """
## Folder-by-Folder Repair Targets

"""

        for folder, count in errors_by_folder.most_common():
            if count > 10:  # Only show folders with significant errors
                percentage = (count / total_errors) * 100
                report += f"""### {folder}/ ({count:,} errors, {percentage:.1f}%)
**Target**: Reduce to <{max(10, count // 2)} errors
**Approach**: Focus on most common error types in this folder
"""

        return report

    def generate_ruff_report(self, analysis_results: dict) -> str:
        """Generate detailed Ruff error report."""
        total_errors = analysis_results["total_errors"]
        errors_by_type = analysis_results["errors_by_type"]
        errors_by_folder = analysis_results["errors_by_folder"]
        errors_by_file = analysis_results["errors_by_file"]

        report = f"""# Ruff Linting Error Analysis Report

## Executive Summary
- **Total Ruff Errors:** {total_errors:,}
- **Unique Error Types:** {len(errors_by_type)}
- **Affected Folders:** {len(errors_by_folder)}
- **Affected Files:** {len(errors_by_file)}

## Error Breakdown by Type

| Error Code | Count | Percentage | Auto-Fix | Priority | Description |
|------------|-------|------------|----------|----------|-------------|
"""

        # Sort by count (descending)
        for error_type, count in errors_by_type.most_common():
            percentage = (count / total_errors) * 100 if total_errors > 0 else 0
            auto_fix = "✅ Yes" if self._is_ruff_auto_fixable(error_type) else "❌ Manual"
            priority = self._get_ruff_priority(error_type)
            description = self._get_ruff_description(error_type)
            report += f"| `{error_type}` | {count:,} | {percentage:.1f}% | {auto_fix} | {priority} | {description} |\n"

        report += """
## Error Breakdown by Folder

| Folder | Count | Percentage | Auto-Fix Potential |
|--------|-------|------------|-------------------|
"""

        for folder, count in errors_by_folder.most_common():
            percentage = (count / total_errors) * 100 if total_errors > 0 else 0
            # Estimate auto-fix potential based on error types in this folder
            auto_fix_potential = "🟢 High" if count < 50 else "🟡 Medium" if count < 200 else "🔴 Low"
            report += f"| `{folder}/` | {count:,} | {percentage:.1f}% | {auto_fix_potential} |\n"

        report += f"""
## Auto-Fix Opportunities

### ✅ Auto-Fixable Errors ({
            sum(count for error_type, count in errors_by_type.items() if self._is_ruff_auto_fixable(error_type))
        } total)
"""

        auto_fixable = [(t, c) for t, c in errors_by_type.most_common() if self._is_ruff_auto_fixable(t)]
        for error_type, count in auto_fixable:
            report += f"- **{error_type}** ({count} errors): Run `ruff check --fix`\n"

        report += f"""
### ❌ Manual Fix Required ({
            sum(count for error_type, count in errors_by_type.items() if not self._is_ruff_auto_fixable(error_type))
        } total)
"""

        manual_fixes = [(t, c) for t, c in errors_by_type.most_common() if not self._is_ruff_auto_fixable(t)][:10]
        for error_type, count in manual_fixes:
            report += f"- **{error_type}** ({count} errors): {self._get_ruff_fix_suggestion(error_type)}\n"

        report += """
## Repair Strategy

### Phase 1: Auto-Fix (Est. 15 minutes)
```bash
# Run auto-fixes
uv run ruff check --fix
uv run ruff format

# Verify changes
git diff
```

### Phase 2: High-Priority Manual Fixes (Est. 2-4 hours)
"""

        high_priority = [(t, c) for t, c in manual_fixes if self._get_ruff_priority(t) == "🔴 High"]
        for error_type, count in high_priority:
            report += f"- Focus on **{error_type}** errors ({count} instances)\n"

        report += """
### Phase 3: Systematic Cleanup (Est. 1-2 days)
"""

        medium_priority = [(t, c) for t, c in manual_fixes if self._get_ruff_priority(t) == "🟡 Medium"][:5]
        for error_type, count in medium_priority:
            report += f"- Address **{error_type}** errors ({count} instances)\n"

        return report

    def _get_mypy_priority(self, error_type: str) -> str:
        """Get priority level for MyPy error types."""
        high_priority = ["import-untyped", "attr-defined", "name-defined", "return-value"]
        medium_priority = ["misc", "union-attr", "assignment", "arg-type", "var-annotated"]

        if error_type in high_priority:
            return "🔴 High"
        elif error_type in medium_priority:
            return "🟡 Medium"
        else:
            return "🟢 Low"

    def _get_mypy_description(self, error_type: str) -> str:
        """Get description for MyPy error codes."""
        descriptions = {
            "import-untyped": "Missing type stubs for imported libraries",
            "attr-defined": "Attribute not defined on object",
            "misc": "Miscellaneous type checking issues",
            "union-attr": "Attribute access on union type without checking",
            "assignment": "Incompatible types in assignment",
            "arg-type": "Incompatible argument type",
            "name-defined": "Name is not defined",
            "return-value": "Missing return statement",
            "var-annotated": "Variable needs type annotation",
            "operator": "Unsupported operand types",
            "index": "Invalid indexing operation",
            "type-var": "Issues with type variables",
            "override": "Method override signature mismatch",
            "call-overload": "No matching overload",
            "valid-type": "Invalid type specification",
        }
        return descriptions.get(error_type, "Type checking issue")

    def _get_mypy_fix_suggestion(self, error_type: str) -> str:
        """Get fix suggestions for MyPy errors."""
        suggestions = {
            "import-untyped": "Install type stubs with `pip install types-<package>`",
            "attr-defined": "Check model field names and imports",
            "misc": "Review complex type issues case by case",
            "union-attr": "Add None checks before attribute access",
            "assignment": "Fix type mismatches in assignments",
            "arg-type": "Add correct parameter type hints",
            "name-defined": "Add missing imports or variable definitions",
            "return-value": "Add return statements to functions",
            "var-annotated": "Add type annotations to variables",
        }
        return suggestions.get(error_type, "Review and fix type issues")

    def _is_ruff_auto_fixable(self, error_code: str) -> bool:
        """Check if Ruff error is auto-fixable."""
        auto_fixable_codes = {
            "F401",
            "F402",
            "F403",
            "F404",
            "F405",  # Import issues
            "E101",
            "E111",
            "E112",
            "E113",
            "E114",
            "E115",
            "E116",
            "E117",  # Indentation
            "E201",
            "E202",
            "E203",
            "E211",
            "E221",
            "E222",
            "E223",
            "E224",
            "E225",  # Whitespace
            "E226",
            "E227",
            "E228",
            "E231",
            "E251",
            "E261",
            "E262",
            "E265",
            "E266",
            "E271",
            "E272",
            "E273",
            "E274",
            "E275",
            "W191",
            "W291",
            "W292",
            "W293",  # Whitespace warnings
            "I001",
            "I002",  # Import sorting
        }
        return error_code in auto_fixable_codes

    def _get_ruff_priority(self, error_code: str) -> str:
        """Get priority level for Ruff error codes."""
        high_priority = ["F821", "F822", "F823", "E999", "F631", "F632"]  # Syntax/name errors
        medium_priority = ["F401", "F841", "E501", "C901"]  # Import/complexity issues

        if error_code in high_priority:
            return "🔴 High"
        elif error_code in medium_priority:
            return "🟡 Medium"
        else:
            return "🟢 Low"

    def _get_ruff_description(self, error_code: str) -> str:
        """Get description for Ruff error codes."""
        descriptions = {
            "F401": "Unused import",
            "F841": "Unused variable",
            "E501": "Line too long",
            "C901": "Function too complex",
            "F821": "Undefined name",
            "E999": "Syntax error",
            "W293": "Blank line contains whitespace",
            "W291": "Trailing whitespace",
            "I001": "Import block not sorted",
            "E402": "Module level import not at top",
        }
        return descriptions.get(error_code, "Code style or logic issue")

    def _get_ruff_fix_suggestion(self, error_code: str) -> str:
        """Get fix suggestions for Ruff errors."""
        suggestions = {
            "F401": "Remove unused imports",
            "F841": "Remove unused variables or prefix with _",
            "E501": "Break long lines or use # noqa: E501",
            "C901": "Simplify complex functions",
            "F821": "Define missing variables or add imports",
            "E999": "Fix syntax errors",
        }
        return suggestions.get(error_code, "Follow Ruff documentation for fixes")

    def generate_combined_report(self, mypy_results: dict, ruff_results: dict) -> str:
        """Generate combined repair target report."""
        return f"""# Code Quality Repair Targets

## Overview
- **MyPy Errors:** {mypy_results["total_errors"]:,}
- **Ruff Errors:** {ruff_results["total_errors"]:,}
- **Total Issues:** {mypy_results["total_errors"] + ruff_results["total_errors"]:,}

## Recommended Repair Sequence

### 1. Quick Wins (Est. 30 minutes)
- Run `uv run ruff check --fix` to auto-fix {
            sum(
                count
                for error_type, count in ruff_results["errors_by_type"].items()
                if self._is_ruff_auto_fixable(error_type)
            )
        } Ruff issues
- Install missing type stubs: `pip install types-polib types-other-packages` ({
            ruff_results["errors_by_type"].get("import-untyped", 0)
        } MyPy errors)

### 2. High-Impact Targets (Est. 2-4 hours)
- **MyPy `attr-defined`**: {mypy_results["errors_by_type"].get("attr-defined", 0)} errors - Fix model field references
- **MyPy `name-defined`**: {mypy_results["errors_by_type"].get("name-defined", 0)} errors - Add missing imports
- **Ruff manual fixes**: {
            sum(
                count
                for error_type, count in ruff_results["errors_by_type"].items()
                if not self._is_ruff_auto_fixable(error_type)
            )
        } errors

### 3. Systematic Cleanup (Est. 1-2 weeks)
- **MyPy `misc`**: {mypy_results["errors_by_type"].get("misc", 0)} errors - Complex type issues
- **Folder-by-folder approach**: Focus on highest error count folders

## Priority Folders for Repair

| Folder | MyPy Errors | Ruff Errors | Total | Priority |
|--------|-------------|-------------|-------|----------|
"""

        # Combine folder errors
        all_folders = set(mypy_results["errors_by_folder"].keys()) | set(ruff_results["errors_by_folder"].keys())
        folder_totals = []

        for folder in all_folders:
            mypy_count = mypy_results["errors_by_folder"].get(folder, 0)
            ruff_count = ruff_results["errors_by_folder"].get(folder, 0)
            total = mypy_count + ruff_count
            folder_totals.append((folder, mypy_count, ruff_count, total))

        folder_totals.sort(key=lambda x: x[3], reverse=True)

        for folder, mypy_count, ruff_count, total in folder_totals[:10]:
            priority = "🔴 High" if total > 300 else "🟡 Medium" if total > 100 else "🟢 Low"
            return f"| `{folder}/` | {mypy_count} | {ruff_count} | {total} | {priority} |\n"

        return ""


def main():
    parser = argparse.ArgumentParser(description="Analyze code quality issues")
    parser.add_argument("--tool", choices=["mypy", "ruff", "both"], default="both", help="Which tool to analyze")
    parser.add_argument("--output", "-o", help="Output file for the report")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")

    args = parser.parse_args()

    analyzer = CodeQualityAnalyzer()

    reports = []

    if args.tool in ["mypy", "both"]:
        print("📊 Analyzing MyPy errors...")
        mypy_results = analyzer.run_mypy_analysis()
        mypy_report = analyzer.generate_mypy_report(mypy_results)
        reports.append(("MyPy", mypy_report, mypy_results))
        print(f"✅ Found {mypy_results['total_errors']} MyPy errors")

    if args.tool in ["ruff", "both"]:
        print("📊 Analyzing Ruff errors...")
        ruff_results = analyzer.run_ruff_analysis()
        ruff_report = analyzer.generate_ruff_report(ruff_results)
        reports.append(("Ruff", ruff_report, ruff_results))
        print(f"✅ Found {ruff_results['total_errors']} Ruff errors")

    # Generate output
    if args.tool == "both" and len(reports) == 2:
        # Combined report
        combined_report = analyzer.generate_combined_report(
            reports[0][2] if reports[0][0] == "MyPy" else reports[1][2],
            reports[1][2] if reports[1][0] == "Ruff" else reports[0][2],
        )
        final_report = combined_report + "\n\n" + "\n\n".join(report[1] for report in reports)
    else:
        final_report = "\n\n".join(report[1] for report in reports)

    if args.output:
        with open(args.output, "w") as f:
            f.write(final_report)
        print(f"📄 Report saved to: {args.output}")
    else:
        print("\n" + final_report)

    # Print summary
    if len(reports) == 2:
        mypy_total = reports[0][2]["total_errors"]
        ruff_total = reports[1][2]["total_errors"]
        total_issues = mypy_total + ruff_total
        print(f"\n📈 Summary: {mypy_total} MyPy + {ruff_total} Ruff = {total_issues} total issues")
    elif len(reports) == 1:
        print(f"\n📈 Summary: {reports[0][2]['total_errors']} {reports[0][0]} issues found")


if __name__ == "__main__":
    main()
