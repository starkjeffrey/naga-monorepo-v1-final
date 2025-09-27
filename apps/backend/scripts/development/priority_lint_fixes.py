#!/usr/bin/env python3
"""Priority linting fixes targeting the most impactful issues for 80% compliance."""

import re
import subprocess
from pathlib import Path


def fix_top_level_imports():
    """Fix PLC0415: import should be at the top-level of a file."""
    for py_file in Path("apps/").rglob("*.py"):
        if py_file.name in ["migrations", "__pycache__"]:
            continue

        try:
            with open(py_file, encoding="utf-8") as f:
                lines = f.readlines()

            # Skip if file is too complex for automatic fix
            if len(lines) > 1000:
                continue

            imports_to_move = []
            new_lines = []

            # Find imports that are not at the top level
            in_function = False
            indent_level = 0

            for i, line in enumerate(lines):
                stripped = line.strip()

                # Track if we're inside a function/class/method
                if stripped.startswith(("def ", "class ", "if __name__")):
                    in_function = True
                    indent_level = len(line) - len(line.lstrip())
                elif in_function and line.strip() and len(line) - len(line.lstrip()) <= indent_level:
                    if not stripped.startswith(
                        (
                            "def ",
                            "class ",
                            "if ",
                            "elif ",
                            "else",
                            "try:",
                            "except",
                            "finally:",
                        ),
                    ):
                        in_function = False

                # Check for imports inside functions that could be moved
                if (
                    in_function
                    and (stripped.startswith(("from ", "import ")))
                    and "apps." in stripped
                    and "# noqa" not in stripped
                ):
                    # Simple heuristic: if import is at start of function, it might be moveable
                    if i > 0 and lines[i - 1].strip().startswith("def "):
                        imports_to_move.append(stripped)
                        new_lines.append(f"        # TODO: Move import to top level - {stripped}\n")
                        continue

                new_lines.append(line)

            # If we found imports to move, add them to top of file
            if imports_to_move:
                # Find where to insert imports (after existing imports)
                insert_pos = 0
                for i, line in enumerate(new_lines):
                    if (
                        line.strip().startswith(("from ", "import "))
                        or line.strip().startswith('"""')
                        or line.strip().startswith("'''")
                        or line.strip().startswith("#")
                    ):
                        insert_pos = i + 1
                    elif line.strip():
                        break

                # Insert the moved imports
                for imp in reversed(imports_to_move):
                    new_lines.insert(insert_pos, f"{imp}\n")

                with open(py_file, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)

        except Exception:
            pass


def fix_logging_fstrings():
    """Fix G004: Logging statement uses f-string."""
    logging_patterns = [
        (r'logger\.info\(f"([^"]*?)"\)', r'logger.info("\1")'),
        (r'logger\.debug\(f"([^"]*?)"\)', r'logger.debug("\1")'),
        (r'logger\.warning\(f"([^"]*?)"\)', r'logger.warning("\1")'),
        (r'logger\.error\(f"([^"]*?)"\)', r'logger.error("\1")'),
        (r'logging\.info\(f"([^"]*?)"\)', r'logging.info("\1")'),
        (r'logging\.debug\(f"([^"]*?)"\)', r'logging.debug("\1")'),
        (r'logging\.warning\(f"([^"]*?)"\)', r'logging.warning("\1")'),
        (r'logging\.error\(f"([^"]*?)"\)', r'logging.error("\1")'),
    ]

    for py_file in Path("apps/").rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Simple replacements for f-strings without variables
            for pattern, replacement in logging_patterns:
                if "{" not in content:  # Only fix simple cases without variables
                    content = re.sub(pattern, replacement, content)

            if content != original_content:
                with open(py_file, "w", encoding="utf-8") as f:
                    f.write(content)

        except Exception:
            pass


def fix_magic_values():
    """Fix PLR2004: Magic value used in comparison - conservative approach."""
    # Only fix very obvious cases
    magic_replacements = {
        # Common constants that are clearly magic
        r"== 0\b": "== 0  # Empty/zero check",
        r"== 1\b": "== 1  # Single item check",
        r"> 0\b": "> 0   # Positive check",
        r">= 1\b": ">= 1  # At least one",
    }

    for py_file in Path("apps/").rglob("*.py"):
        if "/test" in str(py_file) or py_file.name.startswith("test_"):
            continue  # Skip test files

        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Only apply very safe replacements with comments
            for pattern, replacement in magic_replacements.items():
                # Only in if statements to be safe
                # Create closure to capture pattern and replacement
                def make_replacer(pat, repl):
                    def replacer(m):
                        return m.group(0).replace(pat.split("\\b")[0], repl)

                    return replacer

                content = re.sub(f"if .* {pattern}", make_replacer(pattern, replacement), content)

            if content != original_content and len(content) - len(original_content) < 200:  # Sanity check
                with open(py_file, "w", encoding="utf-8") as f:
                    f.write(content)

        except Exception:
            pass


def run_safe_auto_fixes():
    """Run ruff's safest automatic fixes."""
    safe_fixes = [
        "F401",  # unused imports
        "F841",  # unused variables
        "I001",  # import ordering
        "W291",  # trailing whitespace
        "W292",  # no newline at end of file
        "W293",  # blank line contains whitespace
        "UP",  # pyupgrade
    ]

    for rule in safe_fixes:
        cmd = ["uv", "run", "ruff", "check", "apps/", "--fix", "--select", rule]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.stdout.strip():
            pass


def main():
    """Run priority fixes."""
    run_safe_auto_fixes()
    fix_logging_fstrings()
    fix_top_level_imports()

    subprocess.run(["uv", "run", "ruff", "format", "apps/"], check=False)


if __name__ == "__main__":
    main()
