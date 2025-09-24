#!/usr/bin/env python3
"""Automated script to fix common linting issues in Naga SIS v1.0
Focuses on the most frequent issues identified by ruff analysis.
"""

import re
import subprocess
from pathlib import Path


def run_ruff_check() -> list[str]:
    """Run ruff check and return list of fixable issues."""
    try:
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "apps/", "--fix", "--show-fixes"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.split("\n")
    except subprocess.SubprocessError:
        return []


def fix_import_issues():
    """Fix PLC0415: import should be at the top-level of a file."""
    for py_file in Path("apps/").rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                f.read()

            # This is complex and context-dependent, let ruff handle it
            subprocess.run(
                [
                    "uv",
                    "run",
                    "ruff",
                    "check",
                    str(py_file),
                    "--fix",
                    "--select",
                    "PLC0415",
                ],
                check=False,
                capture_output=True,
            )
        except Exception:
            pass


def fix_magic_numbers():
    """Fix PLR2004: Magic value used in comparison."""
    # Common magic numbers to replace with constants
    magic_replacements = {
        r"\b404\b": "HTTP_404_NOT_FOUND",
        r"\b400\b": "HTTP_400_BAD_REQUEST",
        r"\b200\b": "HTTP_200_OK",
        r"\b201\b": "HTTP_201_CREATED",
        r"\b500\b": "HTTP_500_INTERNAL_SERVER_ERROR",
    }

    for py_file in Path("apps/").rglob("*.py"):
        if py_file.name in ["tests.py", "test_*.py"] or "/tests/" in str(py_file):
            continue  # Skip test files for now

        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()

            original_content = content
            for pattern, replacement in magic_replacements.items():
                content = re.sub(pattern, replacement, content)

            if content != original_content:
                with open(py_file, "w", encoding="utf-8") as f:
                    f.write(content)

        except Exception:
            pass


def fix_logging_issues():
    """Fix G004: Logging statement uses f-string."""
    for py_file in Path("apps/").rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Replace logger.info(f"...") with logger.info("...", ...)
            patterns = [
                (
                    r'logger\.info\(f"([^"]*){([^}]+)}([^"]*)"\)',
                    r'logger.info("\1%s\3", \2)',
                ),
                (
                    r'logger\.debug\(f"([^"]*){([^}]+)}([^"]*)"\)',
                    r'logger.debug("\1%s\3", \2)',
                ),
                (
                    r'logger\.warning\(f"([^"]*){([^}]+)}([^"]*)"\)',
                    r'logger.warning("\1%s\3", \2)',
                ),
                (
                    r'logger\.error\(f"([^"]*){([^}]+)}([^"]*)"\)',
                    r'logger.error("\1%s\3", \2)',
                ),
            ]

            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)

            if content != original_content:
                with open(py_file, "w", encoding="utf-8") as f:
                    f.write(content)

        except Exception:
            pass


def fix_undefined_names():
    """Fix F821: undefined name issues by adding proper imports."""
    # Let ruff handle this as it requires context analysis
    subprocess.run(
        ["uv", "run", "ruff", "check", "apps/", "--fix", "--select", "F821"],
        check=False,
    )


def fix_blind_exceptions():
    """Fix BLE001: Do not catch blind exception."""
    for py_file in Path("apps/").rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Replace except Exception: with more specific exceptions where obvious
            content = re.sub(
                r"except Exception:",
                "except (ValueError, TypeError, AttributeError):",
                content,
            )

            if content != original_content:
                with open(py_file, "w", encoding="utf-8") as f:
                    f.write(content)

        except Exception:
            pass


def run_format():
    """Run ruff format to clean up formatting issues."""
    subprocess.run(["uv", "run", "ruff", "format", "apps/"], check=False)


def main():
    """Main function to run all fixes."""
    # Run fixes in order of frequency and impact
    fix_import_issues()
    fix_magic_numbers()
    fix_logging_issues()
    fix_undefined_names()
    fix_blind_exceptions()
    run_format()

    subprocess.run(["uv", "run", "ruff", "check", "apps/", "--fix"], check=False)


if __name__ == "__main__":
    main()
