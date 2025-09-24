#!/usr/bin/env python3
"""
Simple MyPy Error Counter - Bypass Django Plugin Issues

Runs MyPy without Django plugin to get error counts during acceleration.
This allows us to measure progress even when Django configuration is problematic.

Usage:
    python scripts/utilities/simple_mypy_check.py
    python scripts/utilities/simple_mypy_check.py --file apps/people/models.py
"""

import argparse
import re
import subprocess
import tempfile
from pathlib import Path


def create_simple_mypy_config() -> str:
    """Create a minimal MyPy config without Django plugin for acceleration."""
    config_content = """
[tool.mypy]
python_version = "3.13"
check_untyped_defs = true
ignore_missing_imports = true
warn_unused_ignores = true
warn_redundant_casts = true
warn_unused_configs = true
explicit_package_bases = true
namespace_packages = true
# Temporarily disabled Django plugin for acceleration
# plugins = ["mypy_django_plugin.main"]

[[tool.mypy.overrides]]
module = "*.migrations.*"
ignore_errors = true

[[tool.mypy.overrides]]
module = "scratchpad.*"
ignore_errors = true

[[tool.mypy.overrides]]
module = "*.tests.*"
ignore_errors = true
"""

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        return f.name


def run_simple_mypy_check(target: str = ".") -> dict:
    """Run MyPy with simple config to get error count."""
    config_file = create_simple_mypy_config()

    try:
        result = subprocess.run(
            ["uv", "run", "mypy", target, f"--config-file={config_file}", "--show-error-codes"],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Count errors
        error_count = 0
        error_lines = []

        for line in result.stderr.split("\n"):
            if "error:" in line:
                error_count += 1
                error_lines.append(line.strip())

        # Get total from summary
        total_errors = 0
        for line in result.stderr.split("\n"):
            if "Found" in line and "errors" in line:
                match = re.search(r"Found (\d+) errors", line)
                if match:
                    total_errors = int(match.group(1))
                    break

        return {
            "total_errors": total_errors,
            "error_count": error_count,
            "error_lines": error_lines,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    except Exception as e:
        return {"total_errors": 0, "error_count": 0, "error_lines": [], "stderr": str(e), "returncode": -1}
    finally:
        # Clean up temp file
        try:
            Path(config_file).unlink()
        except Exception:
            # Ignore cleanup errors if the file was already removed
            pass


def main():
    parser = argparse.ArgumentParser(description="Simple MyPy error counter for acceleration")
    parser.add_argument("--file", help="Check specific file")
    parser.add_argument("--app", help="Check specific app")
    parser.add_argument("--summary-only", action="store_true", help="Show only error count")

    args = parser.parse_args()

    if args.file:
        target = args.file
    elif args.app:
        target = f"apps/{args.app}"
    else:
        target = "."

    print(f"🔍 Running simple MyPy check on: {target}")

    results = run_simple_mypy_check(target)

    if args.summary_only:
        print(f"Found {results['total_errors']} errors")
    else:
        print("📊 Results:")
        print(f"   Total errors: {results['total_errors']}")
        print(f"   Return code: {results['returncode']}")

        if results["stderr"] and not args.summary_only:
            print("   Raw stderr (first 10 lines):")
            for line in results["stderr"].split("\n")[:10]:
                if line.strip():
                    print(f"     {line}")

        if results["error_lines"] and len(results["error_lines"]) > 0:
            print("   Sample errors:")
            for line in results["error_lines"][:5]:
                print(f"     {line}")

            if len(results["error_lines"]) > 5:
                print(f"     ... and {len(results['error_lines']) - 5} more errors")


if __name__ == "__main__":
    main()
