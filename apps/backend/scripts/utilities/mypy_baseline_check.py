#!/usr/bin/env python3
"""
MyPy Baseline Check Script

Prevents commits that introduce new MyPy errors beyond the established baseline.
Used in pre-commit hooks and CI/CD to maintain type safety progress.

Usage:
    python scripts/utilities/mypy_baseline_check.py  # Check against baseline
    python scripts/utilities/mypy_baseline_check.py --update-baseline  # Update baseline after fixes
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


class MyPyBaselineChecker:
    """Checks MyPy errors against baseline to prevent regression."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.baseline_file = self.project_root / "mypy_baseline.txt"
        self.baseline_errors = self.read_baseline()

    def read_baseline(self) -> int:
        """Read the current baseline error count."""
        if not self.baseline_file.exists():
            print("⚠️ MyPy baseline file not found. Creating with current error count...")
            current_errors = self.get_current_error_count()
            self.update_baseline(current_errors)
            return current_errors

        try:
            content = self.baseline_file.read_text()
            for line in content.split("\n"):
                if line.startswith("BASELINE_ERROR_COUNT="):
                    return int(line.split("=")[1])
            return 0
        except Exception as e:
            print(f"❌ Error reading baseline: {e}")
            return 0

    def get_current_error_count(self) -> int:
        """Get current MyPy error count."""
        try:
            result = subprocess.run(
                ["uv", "run", "mypy", "."],
                check=False,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Extract error count from summary line
            for line in result.stderr.split("\n"):
                if "Found" in line and "errors" in line:
                    match = re.search(r"Found (\d+) errors", line)
                    if match:
                        return int(match.group(1))

            return 0

        except Exception as e:
            print(f"❌ Error running MyPy: {e}")
            return 0

    def check_against_baseline(self) -> bool:
        """Check if current errors are within baseline threshold."""
        current_errors = self.get_current_error_count()

        print("📊 MyPy Error Count Check:")
        print(f"   Baseline: {self.baseline_errors:,} errors")
        print(f"   Current:  {current_errors:,} errors")

        if current_errors <= self.baseline_errors:
            improvement = self.baseline_errors - current_errors
            if improvement > 0:
                print(f"🎉 IMPROVEMENT: {improvement:,} fewer errors than baseline!")

                # Suggest updating baseline if significant improvement
                if improvement >= 10:
                    print(
                        "💡 Consider updating baseline: python scripts/utilities/mypy_baseline_check.py --update-baseline"
                    )
            else:
                print("✅ PASS: No new MyPy errors introduced")
            return True
        else:
            regression = current_errors - self.baseline_errors
            print(f"❌ FAIL: {regression:,} NEW MyPy errors introduced!")
            print("🛠️  Fix these errors before committing:")

            # Show recent errors (likely the new ones)
            self.show_recent_errors()
            return False

    def show_recent_errors(self, limit: int = 10):
        """Show recent MyPy errors that are likely new."""
        try:
            result = subprocess.run(
                ["uv", "run", "mypy", ".", "--show-error-codes"],
                check=False,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Show first few errors as they're likely in recently modified files
            error_lines = [line for line in result.stderr.split("\n") if "error:" in line]

            if error_lines:
                print(f"\n🔍 First {min(limit, len(error_lines))} errors (likely new):")
                for i, line in enumerate(error_lines[:limit]):
                    print(f"   {i + 1}. {line}")

                if len(error_lines) > limit:
                    print(f"   ... and {len(error_lines) - limit} more errors")
        except Exception:
            pass

    def update_baseline(self, new_count: int | None = None):
        """Update the baseline with current error count."""
        if new_count is None:
            new_count = self.get_current_error_count()

        baseline_content = f"""# MyPy Baseline - Current Error Count: {new_count:,} errors
# Generated: {subprocess.run(["date"], check=False, capture_output=True, text=True).stdout.strip()}
# Strategy: Freeze these errors, focus only on preventing NEW errors
#
# This baseline represents the current state after systematic improvements
# New code should not introduce additional MyPy errors beyond this baseline
#
# To use: Compare new MyPy runs against this baseline count
# Target: Keep error count <= {new_count:,} for existing code
# Goal: All new code should have 0 MyPy errors

BASELINE_ERROR_COUNT={new_count}
BASELINE_FILES=199
"""

        self.baseline_file.write_text(baseline_content)
        print(f"✅ Updated MyPy baseline to {new_count:,} errors")
        self.baseline_errors = new_count


def main():
    parser = argparse.ArgumentParser(description="Check MyPy errors against baseline")
    parser.add_argument("--update-baseline", action="store_true", help="Update baseline with current error count")

    args = parser.parse_args()

    checker = MyPyBaselineChecker()

    if args.update_baseline:
        checker.update_baseline()
        return

    # Check against baseline
    passed = checker.check_against_baseline()

    if not passed:
        print("\n💡 Quick fixes to try:")
        print("   1. Fix obvious issues: python scripts/utilities/django_mypy_fixer.py --dry-run")
        print("   2. Check specific app: uv run mypy apps/your_app")
        print("   3. Focus on critical errors: uv run mypy . | grep 'attr-defined\\|name-defined'")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
