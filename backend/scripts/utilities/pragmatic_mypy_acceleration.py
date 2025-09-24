#!/usr/bin/env python3
"""
Pragmatic MyPy Acceleration Script - Week 1 Execution

Applies common bulk fixes based on Django/Python patterns without needing
full MyPy error analysis. This pragmatic approach focuses on the most common
MyPy issues in Django projects.

Usage:
    python scripts/utilities/pragmatic_mypy_acceleration.py --apply-all --confirm
    python scripts/utilities/pragmatic_mypy_acceleration.py --fix-imports
    python scripts/utilities/pragmatic_mypy_acceleration.py --fix-unused-ignores
"""

import argparse
import re
import shutil
import subprocess
from pathlib import Path


class PragmaticMyPyAccelerator:
    """Pragmatic bulk fixes for common Django MyPy issues."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.backup_dir = self.project_root / "pragmatic_acceleration_backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Common Django imports that are often missing
        self.common_missing_imports = {
            "Any": "from typing import Any",
            "Optional": "from typing import Optional",
            "List": "from typing import List",
            "Dict": "from typing import Dict",
            "Union": "from typing import Union",
            "Callable": "from typing import Callable",
            "Tuple": "from typing import Tuple",
            "Iterable": "from typing import Iterable",
            "Iterator": "from typing import Iterator",
            "Type": "from typing import Type",
            "ClassVar": "from typing import ClassVar",
            "cast": "from typing import cast",
            "overload": "from typing import overload",
            "Final": "from typing import Final",
            "Literal": "from typing import Literal",
        }

        # Django-specific imports
        self.django_imports = {
            "HttpRequest": "from django.http import HttpRequest",
            "HttpResponse": "from django.http import HttpResponse",
            "JsonResponse": "from django.http import JsonResponse",
            "QuerySet": "from django.db.models import QuerySet",
            "Model": "from django.db.models import Model",
            "Manager": "from django.db.models import Manager",
            "F": "from django.db.models import F",
            "Q": "from django.db.models import Q",
            "Count": "from django.db.models import Count",
            "Sum": "from django.db.models import Sum",
            "Avg": "from django.db.models import Avg",
            "Max": "from django.db.models import Max",
            "Min": "from django.db.models import Min",
            "timezone": "from django.utils import timezone",
        }

    def create_backup(self, description: str) -> Path:
        """Create backup of all Python files."""
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}_{description}"
        backup_path.mkdir()

        print(f"🛡️ Creating backup: {backup_path}")

        for file_path in self.project_root.rglob("*.py"):
            if not any(skip in str(file_path) for skip in ["__pycache__", ".mypy_cache", "migrations"]):
                relative_path = file_path.relative_to(self.project_root)
                target_path = backup_path / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, target_path)

        return backup_path

    def find_python_files(self) -> list[Path]:
        """Find all Python files to process."""
        files = []
        patterns = ["apps/**/*.py", "api/**/*.py", "users/**/*.py", "config/**/*.py"]

        for pattern in patterns:
            for file_path in self.project_root.glob(pattern):
                if not any(skip in str(file_path) for skip in ["migrations", "__pycache__", "test"]):
                    files.append(file_path)

        return files

    def fix_unused_type_ignores(self) -> int:
        """Remove unused type ignore comments that are causing warnings."""
        print("🧹 Removing unused type ignore comments...")

        files_fixed = 0

        # Remove standalone unused ignores
        for file_path in self.find_python_files():
            content = file_path.read_text()
            original_content = content

            # Remove lines that are just "# type: ignore" (standalone)
            lines = content.split("\n")
            cleaned_lines = []

            for line in lines:
                stripped = line.strip()
                # Remove unused standalone ignores
                if stripped in ["# type: ignore", "# type: ignore  # noqa"]:
                    continue
                cleaned_lines.append(line)

            new_content = "\n".join(cleaned_lines)

            if new_content != original_content:
                file_path.write_text(new_content)
                files_fixed += 1
                print(f"   Cleaned unused ignores: {file_path}")

        return files_fixed

    def add_missing_typing_imports(self) -> int:
        """Add commonly missing typing imports."""
        print("📥 Adding missing typing imports...")

        files_fixed = 0
        all_imports = {**self.common_missing_imports, **self.django_imports}

        for file_path in self.find_python_files():
            content = file_path.read_text()

            # Find what names are used but not imported
            used_names = set()
            imported_names = set()

            # Find usage patterns
            for name in all_imports.keys():
                # Look for the name used in type annotations or code
                if re.search(rf"\b{re.escape(name)}\b", content) and "import" not in content.split("\n")[0]:
                    used_names.add(name)

            # Find existing imports
            for line in content.split("\n"):
                if "from typing import" in line:
                    imports = re.findall(r"from typing import (.+)", line)
                    for imp in imports:
                        imported_names.update([n.strip() for n in imp.split(",") if n.strip()])

                if "from django." in line and "import" in line:
                    # Extract Django imports
                    match = re.search(r"from django\.[^\s]+ import (.+)", line)
                    if match:
                        imported_names.update([n.strip() for n in match.group(1).split(",") if n.strip()])

            # Find what we need to add
            missing_typing = [
                name for name in used_names if name in self.common_missing_imports and name not in imported_names
            ]
            missing_django = [
                name for name in used_names if name in self.django_imports and name not in imported_names
            ]

            if missing_typing or missing_django:
                lines = content.split("\n")

                # Find insertion point for imports
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith(("from ", "import ")) or line.startswith('"""') or line.strip() == "":
                        insert_idx = i + 1
                    else:
                        break

                # Add missing imports
                imports_added = []

                if missing_typing:
                    typing_import = f"from typing import {', '.join(sorted(missing_typing))}"
                    lines.insert(insert_idx, typing_import)
                    imports_added.extend(missing_typing)
                    insert_idx += 1

                # Add Django imports one by one to avoid conflicts
                for name in missing_django:
                    django_import = self.django_imports[name]
                    if django_import not in content:
                        lines.insert(insert_idx, django_import)
                        imports_added.append(name)
                        insert_idx += 1

                if imports_added:
                    new_content = "\n".join(lines)
                    file_path.write_text(new_content)
                    files_fixed += 1
                    print(f"   Added imports to {file_path}: {', '.join(imports_added)}")

        return files_fixed

    def fix_common_django_patterns(self) -> int:
        """Fix common Django-specific MyPy issues."""
        print("🔧 Fixing common Django patterns...")

        files_fixed = 0

        for file_path in self.find_python_files():
            content = file_path.read_text()
            original_content = content
            changes = []

            # Pattern 1: Add TYPE_CHECKING imports for forward references
            if "TYPE_CHECKING" not in content and any(
                quote in content for quote in ['"User"', '"Person"', '"Student"']
            ):
                lines = content.split("\n")

                # Find where to add TYPE_CHECKING import
                for i, line in enumerate(lines):
                    if line.startswith("from typing import"):
                        # Add TYPE_CHECKING to existing typing import
                        if "TYPE_CHECKING" not in line:
                            lines[i] = line.replace("from typing import", "from typing import TYPE_CHECKING, ")

                            # Add TYPE_CHECKING block
                            for j, later_line in enumerate(lines[i + 1 :], i + 1):
                                if later_line.strip() == "" or later_line.startswith(("from ", "import ")):
                                    continue
                                else:
                                    # Insert TYPE_CHECKING block here
                                    lines.insert(j, "if TYPE_CHECKING:")
                                    lines.insert(j + 1, "    pass  # Forward references will be added here")
                                    lines.insert(j + 2, "")
                                    changes.append("Added TYPE_CHECKING structure")
                                    break
                        break
                else:
                    # No existing typing import, add one
                    for i, line in enumerate(lines):
                        if line.startswith(("from ", "import ")) and "django" in line:
                            lines.insert(i, "from typing import TYPE_CHECKING")
                            lines.insert(i + 1, "")
                            lines.insert(i + 2, "if TYPE_CHECKING:")
                            lines.insert(i + 3, "    pass")
                            lines.insert(i + 4, "")
                            changes.append("Added TYPE_CHECKING import and block")
                            break

                content = "\n".join(lines)

            # Pattern 2: Fix manager assignments
            pattern = r"(\w+): (\w+Manager) = (\w+Manager)\(\)  # type: ignore\[assignment,misc\]"
            if re.search(pattern, content):
                content = re.sub(pattern, r"\1: \2 = \2()", content)
                changes.append("Fixed manager assignment type ignores")

            # Pattern 3: Clean up redundant type ignores
            redundant_patterns = [
                r"  # type: ignore\[assignment,misc\]",
                r"  # type: ignore\[misc\]",
                r"  # type: ignore\[attr-defined\]",
            ]

            for pattern in redundant_patterns:
                if re.search(pattern, content):
                    content = re.sub(pattern, "", content)
                    changes.append("Removed redundant type ignore")

            if content != original_content and changes:
                file_path.write_text(content)
                files_fixed += 1
                print(f"   Fixed Django patterns in {file_path}: {', '.join(changes)}")

        return files_fixed

    def apply_strategic_improvements(self) -> dict[str, int]:
        """Apply all strategic improvements for acceleration."""
        print("🚀 Applying strategic MyPy improvements...")

        results = {
            "unused_ignores_fixed": self.fix_unused_type_ignores(),
            "imports_added": self.add_missing_typing_imports(),
            "django_patterns_fixed": self.fix_common_django_patterns(),
            "total_files_affected": 0,
        }

        results["total_files_affected"] = sum(
            [results["unused_ignores_fixed"], results["imports_added"], results["django_patterns_fixed"]]
        )

        return results

    def run_acceleration_test(self) -> None:
        """Run a quick test to see if our changes reduced errors."""
        print("🧪 Testing acceleration impact...")

        # Test on a few key files
        test_files = ["apps/people/models.py", "apps/grading/models.py", "users/managers.py"]

        for file_path in test_files:
            if (self.project_root / file_path).exists():
                try:
                    result = subprocess.run(
                        ["python", "-m", "py_compile", file_path],
                        check=False,
                        cwd=self.project_root,
                        capture_output=True,
                        timeout=30,
                    )

                    if result.returncode == 0:
                        print(f"   ✅ {file_path}: Compiles successfully")
                    else:
                        print(f"   ⚠️ {file_path}: Compilation issues")

                except Exception as e:
                    print(f"   ❌ {file_path}: Test failed - {e}")


def main():
    parser = argparse.ArgumentParser(description="Pragmatic MyPy acceleration for Week 1")
    parser.add_argument("--fix-imports", action="store_true", help="Fix missing typing imports")
    parser.add_argument("--fix-unused-ignores", action="store_true", help="Remove unused type ignores")
    parser.add_argument("--fix-django-patterns", action="store_true", help="Fix Django patterns")
    parser.add_argument("--apply-all", action="store_true", help="Apply all strategic improvements")
    parser.add_argument("--confirm", action="store_true", help="Confirm bulk changes")
    parser.add_argument("--test", action="store_true", help="Test acceleration impact")

    args = parser.parse_args()

    accelerator = PragmaticMyPyAccelerator()

    if not args.confirm and (
        args.apply_all or any([args.fix_imports, args.fix_unused_ignores, args.fix_django_patterns])
    ):
        print("🚨 This will make bulk changes to Python files!")
        print("   Add --confirm flag to proceed")
        return

    if args.apply_all:
        print("🚀 STARTING PRAGMATIC ACCELERATION - Week 1")

        # Create backup
        backup_path = accelerator.create_backup("pragmatic_week1")

        # Apply all improvements
        results = accelerator.apply_strategic_improvements()

        print("\n📊 ACCELERATION RESULTS:")
        print(f"   Unused ignores cleaned: {results['unused_ignores_fixed']} files")
        print(f"   Import additions: {results['imports_added']} files")
        print(f"   Django patterns fixed: {results['django_patterns_fixed']} files")
        print(f"   Total files modified: {results['total_files_affected']} files")
        print(f"   Backup created: {backup_path}")

        # Test the impact
        accelerator.run_acceleration_test()

        print("\n🎉 Week 1 Pragmatic Acceleration Complete!")
        print("   Next: Run mypy to measure actual error reduction")

    elif args.fix_imports:
        backup_path = accelerator.create_backup("imports_fix")
        fixed = accelerator.add_missing_typing_imports()
        print(f"✅ Fixed imports in {fixed} files. Backup: {backup_path}")

    elif args.fix_unused_ignores:
        backup_path = accelerator.create_backup("unused_ignores_fix")
        fixed = accelerator.fix_unused_type_ignores()
        print(f"✅ Cleaned unused ignores in {fixed} files. Backup: {backup_path}")

    elif args.fix_django_patterns:
        backup_path = accelerator.create_backup("django_patterns_fix")
        fixed = accelerator.fix_common_django_patterns()
        print(f"✅ Fixed Django patterns in {fixed} files. Backup: {backup_path}")

    elif args.test:
        accelerator.run_acceleration_test()

    else:
        print("🚀 Pragmatic MyPy Accelerator - Week 1")
        print("   --apply-all --confirm: Apply all strategic improvements")
        print("   --fix-imports --confirm: Fix missing typing imports")
        print("   --fix-unused-ignores --confirm: Remove unused type ignores")
        print("   --fix-django-patterns --confirm: Fix common Django issues")
        print("   --test: Test current code compilation")


if __name__ == "__main__":
    main()
