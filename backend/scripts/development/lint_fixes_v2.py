#!/usr/bin/env python3
"""Improved automated script to fix common linting issues in Naga SIS v1.0"""

import subprocess
from pathlib import Path


def fix_imports_and_constants():
    """Fix undefined imports and restore proper constant values."""
    # First, revert the problematic HTTP constant changes
    for py_file in Path("apps/").rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Revert problematic HTTP constants back to numeric values
            replacements = {
                "HTTP_200_OK": "200",
                "HTTP_201_CREATED": "201",
                "HTTP_400_BAD_REQUEST": "400",
                "HTTP_404_NOT_FOUND": "404",
                "HTTP_500_INTERNAL_SERVER_ERROR": "500",
            }

            for old, new in replacements.items():
                content = content.replace(old, new)

            # Add proper imports where needed
            if "from datetime import date" not in content and "date(" in content:
                # Find the import section
                lines = content.split("\n")
                import_section_end = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith("from ") or line.strip().startswith("import "):
                        import_section_end = i
                    elif line.strip() and not line.strip().startswith("#"):
                        break

                # Insert date import
                lines.insert(import_section_end + 1, "from datetime import date")
                content = "\n".join(lines)

            if content != original_content:
                with open(py_file, "w", encoding="utf-8") as f:
                    f.write(content)

        except Exception:
            pass


def run_automatic_fixes():
    """Run ruff's automatic fixes for safe rules."""
    # List of safe rules to auto-fix
    safe_rules = [
        "F401",  # unused imports
        "F402",  # import shadowed by loop var
        "E701",  # multiple statements on one line
        "E702",  # multiple statements on one line (semicolon)
        "W291",  # trailing whitespace
        "W292",  # no newline at end of file
        "W293",  # blank line contains whitespace
        "I001",  # import order
        "I002",  # import sorting
    ]

    for rule in safe_rules:
        cmd = ["uv", "run", "ruff", "check", "apps/", "--fix", "--select", rule]
        subprocess.run(cmd, check=False, capture_output=True)


def run_format():
    """Run ruff format to fix formatting issues."""
    subprocess.run(["uv", "run", "ruff", "format", "apps/"], check=False)


def main():
    """Main function to run targeted fixes."""
    fix_imports_and_constants()
    run_automatic_fixes()
    run_format()

    # Show final status
    subprocess.run(
        ["uv", "run", "ruff", "check", "apps/", "--statistics"],
        capture_output=True,
        text=True,
        check=False,
    )


if __name__ == "__main__":
    main()
