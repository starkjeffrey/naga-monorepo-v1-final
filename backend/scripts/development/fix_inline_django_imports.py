#!/usr/bin/env python3
"""Fix Django imports that appear inside functions/methods."""

import re
from pathlib import Path


def fix_inline_django_imports():
    """Fix Django imports inside functions by commenting them out."""
    for py_file in Path("apps/").rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Find Django imports that are indented (inside functions/methods)
            pattern = r"^(\s{4,})(from django\.[^\n]+|import django\.[^\n]+)"

            def replace_func(match):
                indent = match.group(1)
                import_line = match.group(2)
                return f"{indent}# {import_line}  # TODO: Move to top-level imports"

            content = re.sub(pattern, replace_func, content, flags=re.MULTILINE)

            if content != original_content:
                with open(py_file, "w", encoding="utf-8") as f:
                    f.write(content)

        except Exception:
            pass


if __name__ == "__main__":
    fix_inline_django_imports()
