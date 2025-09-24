#!/usr/bin/env python3
"""
Django MyPy Bulk Pattern Fixer

Automatically fixes common Django MyPy errors using pattern matching
and bulk replacements. Safe, reversible, and focuses on high-frequency patterns.

Usage:
    python scripts/utilities/django_mypy_fixer.py --dry-run  # Preview changes
    python scripts/utilities/django_mypy_fixer.py --fix attr-defined  # Fix specific error type
    python scripts/utilities/django_mypy_fixer.py --app people  # Fix specific app
"""

import argparse
import re
import shutil
from pathlib import Path


class DjangoMyPyFixer:
    """Bulk fixer for common Django MyPy patterns."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.backup_dir = self.project_root / "mypy_fix_backups"

        # Common Django field name corrections (based on actual project models)
        self.field_corrections = {
            # Student/Person model corrections
            "student_number": "student_id",
            "person_number": "person_id",
            # Term model corrections
            "term_id": "code",  # Term uses 'code' not 'term_id'
            "name": "description",  # Many models use 'description' not 'name'
            # Common field name patterns
            "is_enabled": "is_active",
            "created": "created_at",
            "updated": "updated_at",
        }

        # Common import fixes
        self.import_fixes = {
            "from typing import Any": ["Any"],
            "from typing import Optional": ["Optional"],
            "from typing import List": ["List"],
            "from typing import Dict": ["Dict"],
            "from django.contrib.auth.models import User": ["User"],
            "from decimal import Decimal": ["Decimal"],
        }

    def create_backup(self, file_path: Path) -> Path:
        """Create backup of file before modification."""
        self.backup_dir.mkdir(exist_ok=True)
        backup_path = self.backup_dir / f"{file_path.name}.{file_path.stat().st_mtime}"
        shutil.copy2(file_path, backup_path)
        return backup_path

    def fix_attr_defined_errors(self, content: str, file_path: Path) -> tuple[str, list[str]]:
        """Fix attr-defined errors by correcting common field name mistakes."""
        changes = []
        modified_content = content

        for wrong_field, correct_field in self.field_corrections.items():
            # Pattern: object.wrong_field -> object.correct_field
            pattern = rf"(\w+)\.{re.escape(wrong_field)}\b"
            replacement = rf"\1.{correct_field}"

            if re.search(pattern, modified_content):
                modified_content = re.sub(pattern, replacement, modified_content)
                changes.append(f"Fixed field reference: .{wrong_field} → .{correct_field}")

        return modified_content, changes

    def fix_import_errors(self, content: str, file_path: Path) -> tuple[str, list[str]]:
        """Fix missing import errors by adding common Django/Python imports."""
        changes = []
        modified_content = content

        # Check which imports are used but not imported
        used_names = set()
        imported_names = set()

        # Find usage patterns
        for line in content.split("\n"):
            # Find type annotations and usage
            for name in ["Any", "Optional", "List", "Dict", "User", "Decimal"]:
                if re.search(rf"\b{name}\b", line) and "import" not in line:
                    used_names.add(name)

            # Track existing imports
            if "from typing import" in line:
                imports = re.findall(r"from typing import (.+)", line)
                for imp in imports:
                    imported_names.update([n.strip() for n in imp.split(",")])

        # Add missing imports
        missing_imports = used_names - imported_names
        if missing_imports:
            # Find the best place to add imports (after existing imports)
            lines = modified_content.split("\n")
            import_insert_idx = 0

            for i, line in enumerate(lines):
                if line.startswith("from ") or line.startswith("import "):
                    import_insert_idx = i + 1
                elif line.strip() == "":
                    continue
                else:
                    break

            # Group imports by module
            typing_imports = [name for name in missing_imports if name in ["Any", "Optional", "List", "Dict"]]

            if typing_imports:
                import_line = f"from typing import {', '.join(sorted(typing_imports))}"
                lines.insert(import_insert_idx, import_line)
                changes.append(f"Added typing imports: {', '.join(typing_imports)}")
                modified_content = "\n".join(lines)

        return modified_content, changes

    def fix_queryset_returns(self, content: str, file_path: Path) -> tuple[str, list[str]]:
        """Fix QuerySet return type issues by adding list() conversions."""
        changes = []
        modified_content = content

        # Pattern: return Model.objects.filter(...) in functions with List return type
        pattern = r"(def \w+\([^)]*\)\s*->\s*List\[[^\]]+\]:[^}]+?return\s+)(\w+\.objects\.[^(]+\([^)]*\))"

        def replacement_func(match):
            prefix, queryset = match.groups()
            return f"{prefix}list({queryset})"

        new_content = re.sub(pattern, replacement_func, modified_content, flags=re.DOTALL)
        if new_content != modified_content:
            changes.append("Converted QuerySet returns to list() for List return types")
            modified_content = new_content

        return modified_content, changes

    def fix_optional_access(self, content: str, file_path: Path) -> tuple[str, list[str]]:
        """Fix union-attr errors by adding None checks."""
        changes = []
        modified_content = content

        # Pattern: obj.first().field -> obj.first().field if obj.first() else None
        # This is complex and context-dependent, so we'll be conservative

        # Look for simple .first() usage without None checks
        pattern = r"(\w+)\.first\(\)\.(\w+)"

        def check_and_replace(match):
            obj_expr, field = match.groups()
            # Only replace if not already in a conditional
            return f"({obj_expr}.first().{field} if {obj_expr}.first() else None)"

        # Only apply this fix in safe contexts (not in conditionals)
        lines = modified_content.split("\n")
        safe_lines = []

        for line in lines:
            # Skip lines that already have conditionals
            if " if " in line or "try:" in line or "except" in line:
                safe_lines.append(line)
                continue

            if re.search(pattern, line):
                new_line = re.sub(pattern, check_and_replace, line)
                if new_line != line:
                    changes.append("Added None check for .first() access")
                safe_lines.append(new_line)
            else:
                safe_lines.append(line)

        return "\n".join(safe_lines), changes

    def fix_file(self, file_path: Path, error_types: set[str], dry_run: bool = False) -> dict:
        """Fix MyPy errors in a single file."""
        if not file_path.exists() or not file_path.suffix == ".py":
            return {"file": str(file_path), "changes": [], "error": "Invalid file"}

        try:
            content = file_path.read_text(encoding="utf-8")
            original_content = content
            all_changes = []

            # Apply fixes based on requested error types
            if "attr-defined" in error_types:
                content, changes = self.fix_attr_defined_errors(content, file_path)
                all_changes.extend(changes)

            if "name-defined" in error_types:
                content, changes = self.fix_import_errors(content, file_path)
                all_changes.extend(changes)

            if "misc" in error_types:
                content, changes = self.fix_queryset_returns(content, file_path)
                all_changes.extend(changes)

            if "union-attr" in error_types:
                content, changes = self.fix_optional_access(content, file_path)
                all_changes.extend(changes)

            # Write changes if not dry run and content changed
            if not dry_run and content != original_content:
                backup_path = self.create_backup(file_path)
                file_path.write_text(content, encoding="utf-8")
                all_changes.insert(0, f"Backup created: {backup_path}")

            return {
                "file": str(file_path),
                "changes": all_changes,
                "modified": content != original_content,
                "backup": str(backup_path) if not dry_run and content != original_content else None,
            }

        except Exception as e:
            return {"file": str(file_path), "changes": [], "error": str(e)}

    def find_target_files(self, target_path: str) -> list[Path]:
        """Find Python files to process."""
        if target_path.startswith("apps/"):
            # Specific app
            app_path = self.project_root / target_path
            return list(app_path.glob("**/*.py"))
        else:
            # All critical files (based on our strategic focus)
            patterns = ["apps/**/*.py", "api/**/*.py", "users/**/*.py", "config/**/*.py"]
            files = []
            for pattern in patterns:
                files.extend(self.project_root.glob(pattern))

            # Exclude migrations and tests (already excluded in MyPy config)
            return [f for f in files if "migrations" not in str(f) and "test" not in str(f)]


def main():
    parser = argparse.ArgumentParser(description="Bulk fix common Django MyPy errors")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument(
        "--fix",
        choices=["attr-defined", "name-defined", "misc", "union-attr", "all"],
        default="all",
        help="Error types to fix",
    )
    parser.add_argument("--app", help="Target specific app (e.g., 'people')")
    parser.add_argument("--file", help="Target specific file")

    args = parser.parse_args()

    fixer = DjangoMyPyFixer()

    # Determine error types to fix
    if args.fix == "all":
        error_types = {"attr-defined", "name-defined", "misc", "union-attr"}
    else:
        error_types = {args.fix}

    # Determine target files
    if args.file:
        target_files = [Path(args.file)]
    elif args.app:
        target_files = fixer.find_target_files(f"apps/{args.app}")
    else:
        target_files = fixer.find_target_files("apps/")

    print(f"🔧 {'[DRY RUN] ' if args.dry_run else ''}Fixing {len(target_files)} files")
    print(f"🎯 Error types: {', '.join(error_types)}")

    total_changes = 0
    successful_fixes = 0

    for file_path in target_files:
        result = fixer.fix_file(file_path, error_types, args.dry_run)

        if result.get("error"):
            print(f"❌ {result['file']}: {result['error']}")
            continue

        if result["changes"]:
            print(f"✅ {result['file']}:")
            for change in result["changes"]:
                print(f"   - {change}")
            total_changes += len(result["changes"])
            successful_fixes += 1

    print("\n📊 Summary:")
    print(f"   - Files processed: {len(target_files)}")
    print(f"   - Files with changes: {successful_fixes}")
    print(f"   - Total changes: {total_changes}")

    if args.dry_run and total_changes > 0:
        print(f"\n💡 Run without --dry-run to apply {total_changes} changes")
    elif not args.dry_run and total_changes > 0:
        print(f"\n🎉 Applied {total_changes} fixes! Run 'uv run mypy .' to see progress")


if __name__ == "__main__":
    main()
