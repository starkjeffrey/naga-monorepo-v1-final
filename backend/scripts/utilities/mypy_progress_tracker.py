#!/usr/bin/env python3
"""
MyPy Progress Tracking Script

Tracks MyPy error reduction progress against baseline and provides
actionable recommendations for systematic error reduction.

Usage:
    python scripts/utilities/mypy_progress_tracker.py
    python scripts/utilities/mypy_progress_tracker.py --app people
    python scripts/utilities/mypy_progress_tracker.py --weekly-report
"""

import argparse
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


class MyPyProgressTracker:
    """Tracks MyPy error reduction progress and provides recommendations."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.baseline_errors = 1662  # Current baseline after strategic improvements

    def run_mypy_analysis(self, target: str = ".") -> dict:
        """Run MyPy analysis on target and return structured results."""
        print(f"🔍 Analyzing MyPy errors for: {target}")

        try:
            result = subprocess.run(
                ["uv", "run", "mypy", target, "--show-error-codes"],
                check=False,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Parse output for errors
            errors_by_type: Counter[str] = Counter()
            errors_by_app: Counter[str] = Counter()
            errors_by_file: dict[str, list[str]] = defaultdict(list)

            error_pattern = re.compile(r"^([^:]+):(\d+):(?:\d+:)?\s*(error):\s*(.+?)\s*\[([^\]]+)\]")

            # MyPy outputs to stderr, combine both for parsing
            mypy_output = result.stderr + "\n" + result.stdout
            for line in mypy_output.split("\n"):
                match = error_pattern.match(line.strip())
                if match:
                    file_path, line_num, severity, message, error_code = match.groups()

                    # Count by error type
                    errors_by_type[error_code] += 1

                    # Count by app
                    if file_path.startswith("apps/"):
                        app_name = file_path.split("/")[1]
                        errors_by_app[app_name] += 1

                    # Track by file
                    errors_by_file[file_path].append(f"{error_code}: {message}")

            # Get total from summary line
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
                "errors_by_app": errors_by_app,
                "errors_by_file": dict(errors_by_file),
                "target": target,
            }

        except Exception as e:
            print(f"❌ Error running MyPy analysis: {e}")
            return {"total_errors": 0, "errors_by_type": Counter(), "errors_by_app": Counter(), "errors_by_file": {}}

    def generate_progress_report(self, results: dict) -> str:
        """Generate progress report with actionable recommendations."""
        total = results["total_errors"]
        progress = max(0, self.baseline_errors - total)
        progress_pct = (progress / self.baseline_errors) * 100 if self.baseline_errors > 0 else 0

        report = f"""
# MyPy Progress Report - {datetime.now().strftime("%Y-%m-%d")}

## 📊 **Progress Summary**
- **Current Errors:** {total:,}
- **Baseline:** {self.baseline_errors:,} errors
- **Progress:** {progress:,} errors fixed ({progress_pct:.1f}% complete)
- **Target:** 0 errors
- **Remaining:** {total:,} errors

## 🎯 **Priority Actions This Week**

### High-Impact Quick Wins
"""

        # Prioritize error types for fixing
        priority_errors = {
            "attr-defined": "🔴 Critical - Model field references",
            "name-defined": "🔴 Critical - Missing imports/variables",
            "return-value": "🟡 Medium - Fix return type mismatches",
            "assignment": "🟡 Medium - Type assignment fixes",
            "union-attr": "🟡 Medium - Add None checks",
            "arg-type": "🟡 Medium - Function parameter types",
        }

        for error_type, description in priority_errors.items():
            count = results["errors_by_type"].get(error_type, 0)
            if count > 0:
                report += f"- **{error_type}** ({count} errors): {description}\n"

        # App-level recommendations
        if results["errors_by_app"]:
            report += "\n### 🏢 **Focus Apps This Week**\n"
            top_apps = results["errors_by_app"].most_common(5)
            for app, count in top_apps:
                report += f"- **apps/{app}** ({count} errors): `uv run mypy apps/{app}`\n"

        # Most problematic files
        if results["errors_by_file"]:
            report += "\n### 📁 **Top 5 Files to Fix**\n"
            file_counts = {f: len(errors) for f, errors in results["errors_by_file"].items()}
            top_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            for file_path, count in top_files:
                report += f"- **{file_path}** ({count} errors)\n"

        # Weekly goal
        weekly_target = max(0, total - 50)  # Aim to fix 50 errors per week
        report += f"""
## 🗓️ **This Week's Goal**
- **Target:** Reduce from {total:,} to {weekly_target:,} errors
- **Focus:** Fix top 3 error types above
- **Daily goal:** ~7-10 errors per day
- **Commands to run:**
  ```bash
  # Check progress daily
  uv run mypy . | tail -1

  # Focus on high-priority errors
  uv run mypy . | grep "attr-defined\\|name-defined\\|return-value"

  # Work on specific app
  uv run mypy apps/people  # Replace with your focus app
  ```

## 🏆 **Success Metrics**
- ✅ Zero new MyPy errors introduced
- ✅ At least 50 errors fixed this week
- ✅ All team members using VS Code MyPy extensions
- ✅ Focus on business-critical files first
"""
        return report

    def generate_weekly_summary(self) -> str:
        """Generate weekly progress summary for team standup."""
        current_results = self.run_mypy_analysis()

        return f"""
## 📈 **Weekly MyPy Progress Summary**

**Current Status:** {current_results["total_errors"]:,} errors (Target: 0)
**Weekly Progress:** Aiming for 50 error reduction

**Top Priority:**
1. attr-defined errors ({current_results["errors_by_type"].get("attr-defined", 0)} remaining)
2. Focus on apps/{next(iter(current_results["errors_by_app"].most_common(1)))[0] if current_results["errors_by_app"] else "N/A"}

**Team Action:** Everyone should have VS Code MyPy extensions installed
**Goal:** Zero new MyPy errors in any new code
"""


def main():
    parser = argparse.ArgumentParser(description="Track MyPy error reduction progress")
    parser.add_argument("--app", help="Focus analysis on specific app (e.g., 'people')")
    parser.add_argument("--weekly-report", action="store_true", help="Generate weekly summary")
    parser.add_argument("--output", help="Save report to file")

    args = parser.parse_args()

    tracker = MyPyProgressTracker()

    if args.weekly_report:
        report = tracker.generate_weekly_summary()
        print(report)
        return

    # Determine target for analysis
    target = f"apps/{args.app}" if args.app else "."

    # Run analysis
    results = tracker.run_mypy_analysis(target)

    # Generate report
    report = tracker.generate_progress_report(results)

    # Output results
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"📄 Report saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
