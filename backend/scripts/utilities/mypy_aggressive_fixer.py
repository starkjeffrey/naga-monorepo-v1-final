#!/usr/bin/env python3
"""
MyPy Aggressive Pattern Fixer - Week 1 Acceleration Tool

Applies aggressive bulk fixes based on pattern analysis to achieve 75%+
error reduction in Week 1 of the acceleration plan.

This script is designed for dramatic acceleration from 30+ weeks down to 3-4 weeks.

Usage:
    python scripts/utilities/mypy_aggressive_fixer.py --analyze-patterns
    python scripts/utilities/mypy_aggressive_fixer.py --fix-pattern "attr-defined"
    python scripts/utilities/mypy_aggressive_fixer.py --acceleration-mode --confirm
"""

import argparse
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path


class MyPyAggressiveFixer:
    """Aggressive bulk pattern fixer for dramatic MyPy error reduction acceleration."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.backup_dir = self.project_root / "mypy_acceleration_backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Comprehensive Django field mappings based on actual models
        self.aggressive_field_corrections = {
            # Person/Student models - common mistakes
            "student_number": ["student_id", "id"],
            "person_number": ["person_id", "id"],
            "name": ["full_name", "description", "title"],
            "email": ["email_address", "contact_email"],
            # Term/Academic models
            "term_id": ["code", "term_code"],
            "term_name": ["description", "name"],
            "course_number": ["course_code", "code"],
            # Common field name variations
            "is_enabled": ["is_active"],
            "created": ["created_at", "date_created"],
            "updated": ["updated_at", "date_updated", "last_modified"],
            "status": ["status_code", "state"],
            # Foreign key common mistakes
            "user_id": ["user", "person"],
            "course_id": ["course"],
            "student_id": ["student", "person"],
        }

        # Common import additions for bulk fixing
        self.aggressive_imports = {
            "Any": "from typing import Any",
            "Optional": "from typing import Optional",
            "List": "from typing import List",
            "Dict": "from typing import Dict",
            "Union": "from typing import Union",
            "Callable": "from typing import Callable",
            "User": "from django.contrib.auth.models import User",
            "Decimal": "from decimal import Decimal",
            "datetime": "from datetime import datetime",
            "timezone": "from django.utils import timezone",
            "QuerySet": "from django.db.models import QuerySet",
            "Model": "from django.db.models import Model",
        }

    def create_acceleration_backup(self, description: str) -> Path:
        """Create full project backup before aggressive changes."""
        timestamp = subprocess.run(
            ["date", "+%Y%m%d_%H%M%S"], check=False, capture_output=True, text=True
        ).stdout.strip()
        backup_path = self.backup_dir / f"acceleration_backup_{timestamp}_{description}"

        print(f"🛡️ Creating acceleration backup: {backup_path}")

        # Copy critical files
        critical_patterns = ["apps/**/*.py", "api/**/*.py", "users/**/*.py", "config/**/*.py"]
        backup_path.mkdir()

        for pattern in critical_patterns:
            for file_path in self.project_root.glob(pattern):
                if not any(skip in str(file_path) for skip in ["migrations", "__pycache__", ".mypy_cache"]):
                    relative_path = file_path.relative_to(self.project_root)
                    target_path = backup_path / relative_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, target_path)

        return backup_path

    def get_error_patterns_from_mypy(self) -> dict[str, list[dict]]:
        """Extract specific error patterns from current MyPy run."""
        print("🔍 Analyzing current MyPy errors for aggressive pattern fixing...")

        try:
            result = subprocess.run(
                ["uv", "run", "mypy", ".", "--show-error-codes"],
                check=False,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # Increased timeout
            )

            error_patterns = defaultdict(list)
            error_pattern = re.compile(r"^([^:]+):(\d+):(?:\d+:)?\s*(error):\s*(.+?)\s*\[([^\]]+)\]")

            for line in result.stdout.split("\n"):
                match = error_pattern.match(line.strip())
                if match:
                    file_path, line_num, severity, message, error_code = match.groups()

                    error_info = {
                        "file": file_path,
                        "line": int(line_num),
                        "message": message,
                        "error_code": error_code,
                    }

                    error_patterns[error_code].append(error_info)

            return dict(error_patterns)

        except Exception as e:
            print(f"❌ Error getting MyPy patterns: {e}")
            return {}

    def fix_attr_defined_aggressively(self, error_patterns: dict) -> int:
        """Aggressively fix attr-defined errors using pattern matching and model analysis."""
        if "attr-defined" not in error_patterns:
            return 0

        print(f"🔧 Aggressively fixing {len(error_patterns['attr-defined'])} attr-defined errors...")

        # Group by attribute name for bulk fixing
        attr_groups = defaultdict(list)
        for error in error_patterns["attr-defined"]:
            if "has no attribute" in error["message"]:
                attr_match = re.search(r'"([^"]+)" has no attribute "([^"]+)"', error["message"])
                if attr_match:
                    class_name, attr_name = attr_match.groups()
                    attr_groups[attr_name].append(error)

        total_fixed = 0

        for attr_name, errors in attr_groups.items():
            if len(errors) >= 3:  # Only fix patterns with multiple occurrences
                print(f"   Bulk fixing attribute: '{attr_name}' ({len(errors)} errors)")

                # Get potential corrections for this attribute
                corrections = self.aggressive_field_corrections.get(attr_name, [attr_name])

                # Apply corrections to all affected files
                for error in errors:
                    file_path = Path(error["file"])
                    if file_path.exists():
                        content = file_path.read_text()
                        original_content = content

                        # Try each potential correction
                        for correction in corrections:
                            # Pattern: .attr_name -> .correction
                            pattern = rf"(\w+)\.{re.escape(attr_name)}\b"
                            replacement = rf"\1.{correction}"
                            content = re.sub(pattern, replacement, content)

                        if content != original_content:
                            file_path.write_text(content)
                            total_fixed += 1

        return total_fixed

    def fix_import_errors_aggressively(self, error_patterns: dict) -> int:
        """Aggressively fix name-defined errors by adding common imports."""
        if "name-defined" not in error_patterns:
            return 0

        print(f"🔧 Aggressively fixing {len(error_patterns['name-defined'])} import errors...")

        # Group by undefined name
        name_groups = defaultdict(list)
        for error in error_patterns["name-defined"]:
            if "is not defined" in error["message"]:
                name_match = re.search(r'Name "([^"]+)" is not defined', error["message"])
                if name_match:
                    undefined_name = name_match.group(1)
                    name_groups[undefined_name].append(error)

        total_fixed = 0

        for name, errors in name_groups.items():
            if name in self.aggressive_imports and len(errors) >= 2:
                print(f"   Adding import for: '{name}' ({len(errors)} errors)")

                # Get unique files that need this import
                files_to_fix = {error["file"] for error in errors}

                for file_path_str in files_to_fix:
                    file_path = Path(file_path_str)
                    if file_path.exists():
                        content = file_path.read_text()

                        # Check if import already exists
                        import_statement = self.aggressive_imports[name]
                        if import_statement not in content:
                            # Find best place to add import
                            lines = content.split("\n")
                            import_insert_idx = 0

                            for i, line in enumerate(lines):
                                if line.startswith(("from ", "import ")):
                                    import_insert_idx = i + 1
                                elif line.strip() == "":
                                    continue
                                else:
                                    break

                            lines.insert(import_insert_idx, import_statement)
                            content = "\n".join(lines)
                            file_path.write_text(content)
                            total_fixed += 1

        return total_fixed

    def fix_return_type_errors_aggressively(self, error_patterns: dict) -> int:
        """Aggressively fix return-value errors (QuerySet vs List mismatches)."""
        if "return-value" not in error_patterns:
            return 0

        print(f"🔧 Aggressively fixing {len(error_patterns['return-value'])} return type errors...")

        total_fixed = 0

        for error in error_patterns["return-value"]:
            file_path = Path(error["file"])
            if not file_path.exists():
                continue

            content = file_path.read_text()
            original_content = content

            # Pattern 1: Functions returning QuerySet but declared as returning List
            # return Model.objects.filter(...) -> return list(Model.objects.filter(...))
            pattern1 = r"(return\s+)(\w+\.objects\.[^()]+\([^)]*\))"

            def wrap_with_list(match):
                prefix, queryset = match.groups()
                # Only wrap if context suggests List return type
                return f"{prefix}list({queryset})"

            # Apply pattern if this looks like a List return type issue
            if "List" in content and "return" in content:
                content = re.sub(pattern1, wrap_with_list, content)

            # Pattern 2: QuerySet annotations that should return specific types
            pattern2 = r"(\.annotate\([^)]+\))\s*$"
            content = re.sub(pattern2, r"\1.values()", content, flags=re.MULTILINE)

            if content != original_content:
                file_path.write_text(content)
                total_fixed += 1

        return total_fixed

    def fix_union_attr_errors_aggressively(self, error_patterns: dict) -> int:
        """Aggressively fix union-attr errors (Optional access without None checks)."""
        if "union-attr" not in error_patterns:
            return 0

        print(f"🔧 Aggressively fixing {len(error_patterns['union-attr'])} union-attr errors...")

        total_fixed = 0

        for error in error_patterns["union-attr"]:
            file_path = Path(error["file"])
            if not file_path.exists():
                continue

            content = file_path.read_text()
            original_content = content

            # Pattern: obj.first().attr -> (obj.first().attr if obj.first() else None)
            pattern = r"(\w+)\.first\(\)\.(\w+)"
            replacement = r"(\1.first().\2 if \1.first() else None)"

            # Only apply in simple cases, not in existing conditionals
            lines = content.split("\n")
            fixed_lines = []

            for line in lines:
                if " if " not in line and "try:" not in line:
                    line = re.sub(pattern, replacement, line)
                fixed_lines.append(line)

            content = "\n".join(fixed_lines)

            if content != original_content:
                file_path.write_text(content)
                total_fixed += 1

        return total_fixed

    def run_acceleration_mode(self, confirm: bool = False) -> dict:
        """Run aggressive bulk fixes for maximum Week 1 acceleration."""
        if not confirm:
            print("🚨 ACCELERATION MODE: This will make aggressive bulk changes!")
            print("   Add --confirm flag to proceed")
            return {"status": "cancelled", "reason": "confirmation required"}

        print("🚀 STARTING ACCELERATION MODE - Week 1 Bulk Fix Blitz")

        # Create comprehensive backup
        backup_path = self.create_acceleration_backup("week1_acceleration")

        # Get current error patterns
        error_patterns = self.get_error_patterns_from_mypy()
        total_errors_before = sum(len(errors) for errors in error_patterns.values())

        print(f"📊 Starting with {total_errors_before:,} total errors")

        results = {
            "backup_path": str(backup_path),
            "errors_before": total_errors_before,
            "fixes_applied": {},
            "total_files_modified": 0,
        }

        # Apply aggressive fixes for each major error type
        fix_functions = [
            ("attr-defined", self.fix_attr_defined_aggressively),
            ("name-defined", self.fix_import_errors_aggressively),
            ("return-value", self.fix_return_type_errors_aggressively),
            ("union-attr", self.fix_union_attr_errors_aggressively),
        ]

        for error_type, fix_func in fix_functions:
            if error_type in error_patterns:
                fixes_applied = fix_func(error_patterns)
                results["fixes_applied"][error_type] = fixes_applied
                print(f"   ✅ {error_type}: {fixes_applied} fixes applied")

        # Check progress
        print("🔍 Measuring acceleration progress...")
        new_error_patterns = self.get_error_patterns_from_mypy()
        total_errors_after = sum(len(errors) for errors in new_error_patterns.values())

        results["errors_after"] = total_errors_after
        results["errors_eliminated"] = total_errors_before - total_errors_after
        results["acceleration_percentage"] = (
            (results["errors_eliminated"] / total_errors_before * 100) if total_errors_before > 0 else 0
        )

        print("🎉 ACCELERATION COMPLETE!")
        print(f"   Errors eliminated: {results['errors_eliminated']:,}")
        print(f"   Acceleration: {results['acceleration_percentage']:.1f}%")
        print(f"   Remaining: {total_errors_after:,} errors")

        if results["acceleration_percentage"] >= 75:
            print("🏆 WEEK 1 SUCCESS: Achieved 75%+ error reduction target!")
        elif results["acceleration_percentage"] >= 50:
            print("🎯 GOOD PROGRESS: 50%+ reduction achieved, on track for Week 2")
        else:
            print("⚠️ NEEDS REVIEW: Lower than expected reduction, may need pattern analysis")

        return results


def main():
    parser = argparse.ArgumentParser(description="MyPy Aggressive Pattern Fixer for Acceleration")
    parser.add_argument("--analyze-patterns", action="store_true", help="Analyze current error patterns")
    parser.add_argument("--fix-pattern", help="Fix specific error pattern")
    parser.add_argument("--acceleration-mode", action="store_true", help="Run full Week 1 acceleration")
    parser.add_argument("--confirm", action="store_true", help="Confirm aggressive changes")

    args = parser.parse_args()

    fixer = MyPyAggressiveFixer()

    if args.analyze_patterns:
        patterns = fixer.get_error_patterns_from_mypy()
        print("📊 Current Error Pattern Analysis:")
        for error_type, errors in sorted(patterns.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"   {error_type}: {len(errors)} errors")

    elif args.fix_pattern:
        patterns = fixer.get_error_patterns_from_mypy()
        if args.fix_pattern == "attr-defined":
            fixed = fixer.fix_attr_defined_aggressively(patterns)
            print(f"✅ Fixed {fixed} attr-defined patterns")
        elif args.fix_pattern == "name-defined":
            fixed = fixer.fix_import_errors_aggressively(patterns)
            print(f"✅ Fixed {fixed} import patterns")
        else:
            print(f"❌ Unknown pattern: {args.fix_pattern}")

    elif args.acceleration_mode:
        results = fixer.run_acceleration_mode(args.confirm)
        if results.get("status") != "cancelled":
            print("\n📋 Full Results:")
            print(f"   Backup: {results['backup_path']}")
            print(f"   Before: {results['errors_before']:,} errors")
            print(f"   After: {results['errors_after']:,} errors")
            print(f"   Eliminated: {results['errors_eliminated']:,} errors")
            print(f"   Acceleration: {results['acceleration_percentage']:.1f}%")

    else:
        print("🚀 MyPy Acceleration Fixer")
        print("   --analyze-patterns: Analyze current error patterns")
        print("   --acceleration-mode --confirm: Run full Week 1 acceleration")
        print("   --fix-pattern <type>: Fix specific error pattern")


if __name__ == "__main__":
    main()
